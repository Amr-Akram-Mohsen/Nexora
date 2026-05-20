from app.domains.item.service import get_item_by_id
from app.domains.interaction.service import record_view
from app.shared.constants.core import TargetType

from app.infrastructure import cache

@cache.memoize(timeout=600)
def get_item_page_data(item_id):
    """
    Orchestrates data for a single item page.
    """
    item = get_item_by_id(item_id, serialize=True)
    if not item:
        return None

    return {
        "item": item
    }

def record_item_view(item_id, user, ip_address):
    """
    Records an item view interaction.
    """
    record_view(
        target_id=item_id,
        target_type=TargetType.ITEM,
        user=user,
        ip_address=ip_address
    )
