from app.domains.system.service import (
    get_section_by_slug,
    get_relationships_for_section,
    get_types_for_section,
    get_attributes_for_section,
)
from app.application.content.query_service import get_filtered_contents_cached
from app.infrastructure.cache import normalize_filters


def get_feed_data(section_slug, active_filters, page=1):
    """
    Orchestrates data for a section feed (catalog page).
    """
    section = get_section_by_slug(section_slug)
    if not section:
        return None

    from app.domains.serializers import serialize_model

    allowed_filters = section.allowed_filters
    pagination = get_filtered_contents_cached(
        section.id,
        normalize_filters(active_filters),
        tuple(allowed_filters or []),
        page=page,
    )

    filter_options = {}
    if "category" in allowed_filters:
        filter_options["category"] = get_relationships_for_section(
            section_slug, "category"
        )
    if "brand" in allowed_filters:
        filter_options["brand"] = get_relationships_for_section(section_slug, "brand")
    if "topic" in allowed_filters:
        filter_options["topic"] = get_relationships_for_section(section_slug, "topic")
    if "intent" in allowed_filters:
        filter_options["intent"] = get_relationships_for_section(section_slug, "intent")
    if "price_tier" in allowed_filters:
        filter_options["price_tier"] = get_relationships_for_section(
            section_slug, "price_tier"
        )
    if "type" in allowed_filters:
        filter_options["type"] = get_types_for_section(section_slug)
    if "attributes" in allowed_filters:
        category_slugs = active_filters.get("category", [])
        filter_options["attributes"] = get_attributes_for_section(
            section_slug, category_slugs=category_slugs
        )

    return {
        "section": serialize_model(section),
        "contents": pagination["items"],
        "pagination": pagination,
        "allowed_filters": allowed_filters,
        "filter_options": filter_options,
    }
