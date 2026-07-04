from app.domains.taxonomy.service import (
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
    relationship_filters = ["category", "brand", "topic", "intent", "price_tier"]
    
    for f in relationship_filters:
        if f in allowed_filters:
            filter_options[f] = get_relationships_for_section(section_slug, f)
            
    if "type" in allowed_filters:
        filter_options["type"] = get_types_for_section(section_slug)
    if "attributes" in allowed_filters:
        category_slugs = active_filters.get("category", [])
        filter_options["attributes"] = get_attributes_for_section(
            section_slug, category_slugs=category_slugs
        )
    has_results = len(pagination["items"]) > 0
    from app.application.recommendation.contextual import get_contextual_recommendations
    recommendation_blocks = get_contextual_recommendations(
        active_filters, has_results, section=section, target_type="content"
    )

    return {
        "section": serialize_model(section),
        "contents": pagination["items"],
        "pagination": pagination,
        "allowed_filters": allowed_filters,
        "filter_options": filter_options,
        "recommendations": recommendation_blocks,
    }

