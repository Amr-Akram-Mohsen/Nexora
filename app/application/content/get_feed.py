from app.domains.taxonomy.service import (
    get_section_by_slug,
    get_taxonomy_filters,
)
from app.application.content.query_service import get_filtered_contents_cached
from app.infrastructure.cache import normalize_filters


def get_feed_data(section_slug, active_filters, page=1):
    """
    Orchestrates data for a section feed (catalog page).
    """
    if section_slug == "all":
        class MockSection:
            id = None
            name = "All Content"
            slug = "all"
            allowed_filters = ["category", "entity", "intent", "price_tier", "type", "attributes", "source", "event", "author", "location"]
        section = MockSection()
    else:
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

    category_slugs = active_filters.get("category", [])
    if isinstance(category_slugs, list):
        category_slugs = tuple(sorted(category_slugs))
    elif isinstance(category_slugs, str):
        category_slugs = (category_slugs,)
        
    filter_options = get_taxonomy_filters(
        section_slug, 
        tuple(allowed_filters or []), 
        category_slugs
    )
    has_results = len(pagination["products"]) > 0
    from app.application.recommendation.contextual import get_contextual_recommendations
    recommendation_blocks = get_contextual_recommendations(
        active_filters, has_results, section=section, target_type="content"
    )

    return {
        "section": serialize_model(section),
        "contents": pagination["products"],
        "pagination": pagination,
        "allowed_filters": allowed_filters,
        "filter_options": filter_options,
        "recommendations": recommendation_blocks,
    }

def get_source_feed_data(source_slug, page=1):
    from app.domains.taxonomy.models import Source
    from app.core.extensions import db
    from app.domains.serializers import serialize_model

    source = db.session.query(Source).filter_by(slug=source_slug).first()
    if not source:
        return None

    pagination = get_filtered_contents_cached(
        None,
        normalize_filters({"source": [source_slug]}),
        ("source",),
        page=page,
    )

    return {
        "source": serialize_model(source),
        "contents": pagination["products"],
        "pagination": pagination,
        "allowed_filters": [],
        "filter_options": {},
        "recommendations": [],
    }

