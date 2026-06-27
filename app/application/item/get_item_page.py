from app.domains.item.service import get_item_by_id, get_related_items, serialize_item
from app.domains.item.service.serializers import serialize_item_detail
from app.domains.interaction.service import record_view
from app.shared.constants.core import TargetType
from app.infrastructure.cache import cache
from app.application.recommendation.query_service import get_contents_for_item_cached

@cache.memoize(timeout=1800)
def get_item_page_data(item_id):
    """Item page orchestration: single DB load.

    Previously this module issued:
      1. get_item_by_id(serialize=True)   → ORM load + serialize
      2. get_item_by_id(serialize=False)  → second ORM load (same item!)
      3. db.session.query(Item.view_count) → third scalar query

    Now we load the raw ORM object exactly once, serialize it in-process,
    and reuse the same object for get_related_items. view_count is already
    included by serialize_item_detail.
    """
    raw_item = get_item_by_id(item_id, serialize=False, load="detail")
    if not raw_item:
        return None

    item = serialize_item_detail(raw_item)
    related = get_related_items(raw_item)

    # Content articles/reviews that reference this item (Content↔Item matcher)
    related_contents = get_contents_for_item_cached(item_id, limit=12)

    related_articles = []
    related_videos = []
    buying_guides = []

    for c in related_contents:
        section_slug = c.get("section", {}).get("slug") if c.get("section") else None
        if c.get("object_type") == "video":
            related_videos.append(c)
        elif c.get("object_type") == "article" and section_slug == "tutorials":
            buying_guides.append(c)
        elif c.get("object_type") == "article":
            related_articles.append(c)

    return {
        "item": item,
        "variant_data": item.get("variant_data", []),
        "related_items": [serialize_item(i) for i in related],
        "related_contents": related_contents,
        "related_articles": related_articles,
        "related_videos": related_videos,
        "buying_guides": buying_guides,
    }


def record_item_view(item_id, user, ip_address):
    """Records an item view interaction."""
    record_view(
        target_id=item_id,
        target_type=TargetType.ITEM,
        user=user,
        ip_address=ip_address,
    )
    from app.core.extensions import db
    db.session.commit()
