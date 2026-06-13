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
    recommendation_blocks = get_item_recommendations(active_filters, has_results)

    return {
        "items": pagination.get("items", []),
        "pagination": pagination,
        "filter_options": filter_options,
        "recommendations": recommendation_blocks,
    }


def get_item_recommendations(active_filters, has_results):
    from app.application.recommendation.query_service import (
        get_popular_contents_cached,
        get_popular_items_cached,
    )

    category_slugs = active_filters.get("category", [])
    brand_slugs = active_filters.get("brand", [])

    blocks = []

    cat_name = category_slugs[0].replace("-", " ").title() if category_slugs else ""
    brand_name = brand_slugs[0].replace("-", " ").title() if brand_slugs else ""

    if has_results:
        # Results exist
        if category_slugs:
            cat_contents = get_popular_contents_cached(
                category_slugs=tuple(category_slugs),
                limit=6
            )
            if cat_contents:
                blocks.append({
                    "title": f"Trending {cat_name} Content",
                    "type": "content",
                    "items": cat_contents
                })

            cat_products = get_popular_items_cached(
                category_slugs=tuple(category_slugs),
                limit=6
            )
            if cat_products:
                blocks.append({
                    "title": f"Popular {cat_name} Products",
                    "type": "item",
                    "items": cat_products
                })

        elif brand_slugs:
            brand_contents = get_popular_contents_cached(
                brand_slugs=tuple(brand_slugs),
                limit=6
            )
            if brand_contents:
                blocks.append({
                    "title": f"Trending {brand_name} Content",
                    "type": "content",
                    "items": brand_contents
                })

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
        else:
            # No specific filter active
            trending_products = get_popular_items_cached(limit=6)
            if trending_products:
                blocks.append({
                    "title": "Trending Products",
                    "type": "item",
                    "items": trending_products
                })

            trending_reviews = get_popular_contents_cached(
                intent_slugs=("review",),
                limit=6
            )
            if trending_reviews:
                blocks.append({
                    "title": "Trending Reviews",
                    "type": "content",
                    "items": trending_reviews
                })

    else:
        # Empty state recovery (Zero Results)
        if category_slugs:
            cat_alternatives = get_popular_items_cached(
                category_slugs=tuple(category_slugs),
                limit=6
            )
            if cat_alternatives:
                blocks.append({
                    "title": f"Popular Alternatives in {cat_name}",
                    "type": "item",
                    "items": cat_alternatives
                })

            cat_content = get_popular_contents_cached(
                category_slugs=tuple(category_slugs),
                limit=6
            )
            if cat_content:
                blocks.append({
                    "title": f"Trending {cat_name} Content",
                    "type": "content",
                    "items": cat_content
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
            trending_products = get_popular_items_cached(limit=6)
            if trending_products:
                blocks.append({
                    "title": "Trending Products",
                    "type": "item",
                    "items": trending_products
                })

            trending_reviews = get_popular_contents_cached(
                intent_slugs=("review",),
                limit=6
            )
            if trending_reviews:
                blocks.append({
                    "title": "Trending Reviews",
                    "type": "content",
                    "items": trending_reviews
                })

    return blocks

