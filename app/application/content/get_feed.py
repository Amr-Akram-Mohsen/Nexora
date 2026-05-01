from app.domains.system.service import (
    get_section_by_slug,
    get_active_brands_for_section,
    get_active_topics_for_section,
    get_active_categories_for_section
)
from app.domains.content.service import get_filtered_contents

def get_feed_data(section_slug, active_filters, page=1):
    """
    Orchestrates data for a section feed (catalog page).
    """
    section = get_section_by_slug(section_slug)
    if not section:
        return None

    allowed_filters = set(section.allowed_filters or [])
    pagination = get_filtered_contents(section, active_filters, allowed_filters, page=page)
    
    filter_options = {}
    if "category" in allowed_filters:
        filter_options["category"] = get_active_categories_for_section(section_slug)
    if "brand" in allowed_filters:
        filter_options["brand"] = get_active_brands_for_section(section_slug)
    if "topic" in allowed_filters:
        filter_options["topic"] = get_active_topics_for_section(section_slug)

    return {
        "section": section,
        "contents": pagination.items,
        "pagination": pagination,
        "allowed_filters": allowed_filters,
        "filter_options": filter_options
    }
