from app.domains.item.service import get_item_by_id
from app.domains.interaction.service import record_view
from app.shared.constants.core import TargetType

def get_item_page_data(item_id, user, ip_address):
    """
    Orchestrates data for a single item page.
    """
    item = get_item_by_id(item_id)
    if not item:
        return None

    record_view(
        target=item,
        target_type=TargetType.ITEM,
        user=user,
        ip_address=ip_address
    )

    return {
        "item": item
    }
