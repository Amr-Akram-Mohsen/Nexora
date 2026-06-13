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
    has_results = len(pagination["items"]) > 0
    recommendation_blocks = get_content_recommendations(section, active_filters, has_results)

    return {
        "section": serialize_model(section),
        "contents": pagination["items"],
        "pagination": pagination,
        "allowed_filters": allowed_filters,
        "filter_options": filter_options,
        "recommendations": recommendation_blocks,
    }


def get_content_recommendations(section, active_filters, has_results):
    from app.application.recommendation.query_service import (
        get_popular_contents_cached,
        get_popular_items_cached,
    )

    category_slugs = active_filters.get("category", [])
    brand_slugs = active_filters.get("brand", [])
    intent_slugs = active_filters.get("intent", [])

    blocks = []

    # Format names for title
    cat_name = category_slugs[0].replace("-", " ").title() if category_slugs else ""
    brand_name = brand_slugs[0].replace("-", " ").title() if brand_slugs else ""
    intent_name = intent_slugs[0].replace("-", " ").title() if intent_slugs else ""

    if has_results:
        # Results exist: Show secondary filter-aware recommendations
        if category_slugs:
            # Category is active
            trending_cat = get_popular_contents_cached(
                section_id=section.id,
                category_slugs=tuple(category_slugs),
                limit=6
            )
            if trending_cat:
                blocks.append({
                    "title": f"Trending {cat_name} Content",
                    "type": "content",
                    "items": trending_cat
                })

            cat_reviews = get_popular_contents_cached(
                category_slugs=tuple(category_slugs),
                intent_slugs=("review",),
                limit=6
            )
            if cat_reviews:
                blocks.append({
                    "title": f"Popular {cat_name} Reviews",
                    "type": "content",
                    "items": cat_reviews
                })

            cat_guides = get_popular_contents_cached(
                category_slugs=tuple(category_slugs),
                intent_slugs=("buying-guide",),
                limit=6
            )
            if cat_guides:
                blocks.append({
                    "title": f"Related Buying Guides",
                    "type": "content",
                    "items": cat_guides
                })

        elif brand_slugs:
            # Brand is active
            brand_products = get_popular_items_cached(
                brand_slugs=tuple(brand_slugs),
                limit=6
            )
            if brand_products:
                blocks.append({
                    "title": f"Popular {brand_name} Products",
                    "type": "item",
                    "items": brand_products
                })

            brand_reviews = get_popular_contents_cached(
                brand_slugs=tuple(brand_slugs),
                intent_slugs=("review",),
                limit=6
            )
            if brand_reviews:
                blocks.append({
                    "title": f"Related {brand_name} Reviews",
                    "type": "content",
                    "items": brand_reviews
                })

            brand_guides = get_popular_contents_cached(
                brand_slugs=tuple(brand_slugs),
                intent_slugs=("buying-guide",),
                limit=6
            )
            if brand_guides:
                blocks.append({
                    "title": f"Related Buying Guides",
                    "type": "content",
                    "items": brand_guides
                })

        elif intent_slugs:
            # Intent is active
            trending_intent = get_popular_contents_cached(
                section_id=section.id,
                intent_slugs=tuple(intent_slugs),
                limit=6
            )
            if trending_intent:
                blocks.append({
                    "title": f"Trending {intent_name}s",
                    "type": "content",
                    "items": trending_intent
                })

            popular_intent = get_popular_contents_cached(
                intent_slugs=tuple(intent_slugs),
                limit=6
            )
            if popular_intent:
                blocks.append({
                    "title": f"Popular {intent_name}s",
                    "type": "content",
                    "items": popular_intent
                })

        else:
            # No specific filter, show section trending
            trending_section = get_popular_contents_cached(
                section_id=section.id,
                limit=6
            )
            if trending_section:
                blocks.append({
                    "title": f"Trending in {section.name}",
                    "type": "content",
                    "items": trending_section
                })

    else:
        # Empty state recovery recommendations (Zero Results)
        if category_slugs:
            # Recover by showing popular alternatives/products in category
            cat_alternatives = get_popular_contents_cached(
                category_slugs=tuple(category_slugs),
                limit=6
            )
            if cat_alternatives:
                blocks.append({
                    "title": f"Popular Alternatives in {cat_name}",
                    "type": "content",
                    "items": cat_alternatives
                })

            cat_products = get_popular_items_cached(
                category_slugs=tuple(category_slugs),
                limit=6
            )
            if cat_products:
                blocks.append({
                    "title": f"Popular Products in {cat_name}",
                    "type": "item",
                    "items": cat_products
                })

        elif brand_slugs:
            brand_products = get_popular_items_cached(
                brand_slugs=tuple(brand_slugs),
                limit=6
            )
            if brand_products:
                blocks.append({
                    "title": f"Popular {brand_name} Products",
                    "type": "item",
                    "items": brand_products
                })

            brand_content = get_popular_contents_cached(
                brand_slugs=tuple(brand_slugs),
                limit=6
            )
            if brand_content:
                blocks.append({
                    "title": f"Trending {brand_name} Content",
                    "type": "content",
                    "items": brand_content
                })

        else:
            # Global fallbacks for recovery
            trending_content = get_popular_contents_cached(
                section_id=section.id,
                limit=6
            )
            if trending_content:
                blocks.append({
                    "title": "Trending Content",
                    "type": "content",
                    "items": trending_content
                })

            popular_products = get_popular_items_cached(
                limit=6
            )
            if popular_products:
                blocks.append({
                    "title": "Popular Products",
                    "type": "item",
                    "items": popular_products
                })

    return blocks

