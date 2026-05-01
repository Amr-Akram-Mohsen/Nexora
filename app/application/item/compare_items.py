from app.domains.item.service import get_items_by_ids

def get_comparison_data(item_ids):
    """
    Orchestrates data for item comparison.
    """
    if not item_ids:
        return None

    # Limit to 4 items for layout sanity
    item_ids = item_ids[:4]
    items = get_items_by_ids(item_ids)
    
    if not items:
        return None

    # Extract all possible specification categories from all items being compared
    all_categories = set()
    for item in items:
        if item.full_details:
            all_categories.update(item.full_details.keys())
    
    return {
        "items": items,
        "all_categories": sorted(list(all_categories))
    }
