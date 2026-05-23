from app.domains.item.service import get_item_by_id, get_related_items, serialize_item
from app.domains.item.service.serializers import serialize_item_detail
from app.domains.interaction.service import record_view
from app.shared.constants.core import TargetType


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

    return {
        "item": item,
        "variant_data": item.get("variant_data", []),
        "related_items": [serialize_item(i) for i in related],
    }


def record_item_view(item_id, user, ip_address):
    """Records an item view interaction."""
    record_view(
        target_id=item_id,
        target_type=TargetType.ITEM,
        user=user,
        ip_address=ip_address,
    )
