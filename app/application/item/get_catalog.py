from app.domains.item.service import get_filtered_items, get_distinct_item_types, get_distinct_stores
from app.domains.system.service import get_distinct_item_categories, get_distinct_item_brands

def get_catalog_data(active_filters, page=1):
    """
    Orchestrates data for the items catalog (deals page).
    """
    pagination = get_filtered_items(active_filters, page=page)
    
    filter_options = {
        "category": get_distinct_item_categories(),
        "brand": get_distinct_item_brands(),
        "store": get_distinct_stores(),
        "type": get_distinct_item_types()
    }

    return {
        "items": pagination.items,
        "pagination": pagination,
        "filter_options": filter_options
    }
