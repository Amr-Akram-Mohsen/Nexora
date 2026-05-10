from app.domains.system.service import (
    get_section_by_slug,
    get_active_brands_for_section,
    get_active_topics_for_section,
    get_active_categories_for_section
)
from app.application.content.query_service import get_filtered_contents

def get_feed_data(section_slug, active_filters, page=1):
    """
    Orchestrates data for a section feed (catalog page).
    """
    section = get_section_by_slug(section_slug)
    if not section:
        return None

    from app.domains.system.service.query import get_allowed_filters
    from app.domains.serializers import serialize_section

    allowed_filters = get_allowed_filters(section)
    pagination = get_filtered_contents(section.id, active_filters, allowed_filters, page=page)
    
    filter_options = {}
    if "category" in allowed_filters:
        filter_options["category"] = get_active_categories_for_section(section_slug)
    if "brand" in allowed_filters:
        filter_options["brand"] = get_active_brands_for_section(section_slug)
    if "topic" in allowed_filters:
        filter_options["topic"] = get_active_topics_for_section(section_slug)
    if "intent" in allowed_filters:
        from app.domains.system.service.query import get_active_intents_for_section
        filter_options["intent"] = get_active_intents_for_section(section_slug)
    if "price_tier" in allowed_filters:
        from app.domains.system.service.query import get_active_price_tiers_for_section
        filter_options["price_tier"] = get_active_price_tiers_for_section(section_slug)
    if "type" in allowed_filters:
        from app.domains.system.service.query import get_active_types_for_section
        filter_options["type"] = get_active_types_for_section(section_slug)

    return {
        "section": serialize_section(section),
        "contents": pagination.items,
        "pagination": pagination,
        "allowed_filters": allowed_filters,
        "filter_options": filter_options
    }
