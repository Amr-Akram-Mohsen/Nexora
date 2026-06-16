from app.domains.item.service import get_filtered_items, get_distinct_item_types, get_distinct_stores
from app.domains.taxonomy.service import get_distinct_item_categories, get_distinct_item_brands
from app.infrastructure.cache import filters_from_normalized, normalize_filters

def get_catalog_data(active_filters, page=1):
    """
    Orchestrates data for the items catalog (deals page).
    """
    canonical_filters = filters_from_normalized(normalize_filters(active_filters))
    pagination = get_filtered_items(canonical_filters, page=page)
    
    filter_options = {
        "category": get_distinct_item_categories(),
        "brand": get_distinct_item_brands(),
        "store": get_distinct_stores(),
        "type": get_distinct_item_types()
    }

    has_results = len(pagination.get("items", [])) > 0
    from app.application.recommendation.contextual import get_contextual_recommendations
    recommendation_blocks = get_contextual_recommendations(
        active_filters, has_results, target_type="item"
    )

    return {
        "items": pagination.get("items", []),
        "pagination": pagination,
        "filter_options": filter_options,
        "recommendations": recommendation_blocks,
    }

