from app.core.extensions import db
from app.domains.item.models import Item
from app.domains.item.service import get_item_by_id
from app.domains.interaction.service import record_view
from app.shared.constants.core import TargetType
from app.infrastructure import cache


@cache.memoize(timeout=1800)
def get_item_static_data(item_id):
    """Cache stable item page payload (specs, images, variants, links)."""
    return get_item_by_id(item_id, serialize=True, load="detail")


def get_item_page_data(item_id):
    """
    Item page orchestration: cached static body + fresh view_count.
    """
    item = get_item_static_data(item_id)
    if not item:
        return None

    view_count = db.session.query(Item.view_count).filter_by(id=item_id).scalar()
    if view_count is not None:
        item = {**item, "view_count": view_count}

    return {"item": item}


def record_item_view(item_id, user, ip_address):
    """Records an item view interaction."""
    record_view(
        target_id=item_id,
        target_type=TargetType.ITEM,
        user=user,
        ip_address=ip_address,
    )
