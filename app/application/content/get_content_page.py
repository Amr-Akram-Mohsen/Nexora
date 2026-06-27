from app.domains.content.service import get_content_by_id
from app.application.content.query_service import (
    get_related_contents_cached,
    get_trending_contents_cached,
)
from app.application.recommendation.query_service import get_items_for_content_cached
from app.domains.interaction.service import record_view
from app.infrastructure import cache
from app.shared.constants.core import TargetType


@cache.memoize(timeout=1800)
def get_content_page_static_data(content_id):
    return get_content_by_id(content_id)


def get_content_page_data(content_id):
    """
    Orchestrates data for a single content/article page.

    Returns:
        content          — serialized content dict
        related_contents — scored related content items
        trending_contents— trending content in the same section
        matched_items    — items matched by the Article↔Item matcher (affil. CTA)
    """
    content = get_content_page_static_data(content_id)
    # content is now a serialized dictionary
    if not content:
        return None

    related_contents = get_related_contents_cached(content["id"])
    
    seen_content_ids = {content["id"]}
    if related_contents:
        seen_content_ids.update(c["id"] for c in related_contents if c.get("id"))

    # section is a serialized dict as well
    section_ids = [content["section_id"]] if content.get("section_id") else None
    trending_contents = get_trending_contents_cached(
        limit=6, days=7, section_ids=section_ids, exclude_ids=tuple(seen_content_ids)
    )

    # Items matched via the Content↔Item matcher — primary affiliate signal
    # Exclude any directly linked items from matched items
    linked_item_ids = {i["id"] for i in content.get("linked_items", []) if i.get("id")}
    matched_items = get_items_for_content_cached(content["id"], limit=6, exclude_ids=tuple(linked_item_ids) if linked_item_ids else None)

    return {
        "content": content,
        "related_contents": related_contents,
        "trending_contents": trending_contents,
        "matched_items": matched_items,
    }


def record_content_view(content_id, user, ip_address):
    """
    Records an article/content view interaction.
    """
    record_view(
        target_id=content_id,
        target_type=TargetType.CONTENT,
        user=user,
        ip_address=ip_address,
    )
    from app.core.extensions import db
    db.session.commit()
