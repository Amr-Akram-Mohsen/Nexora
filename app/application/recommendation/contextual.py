from app.application.recommendation.query_service import (
    get_popular_contents_cached,
    get_popular_items_cached,
)

def get_contextual_recommendations(active_filters, has_results, section=None, target_type="content"):
    """
    Generates contextual recommendation blocks based on active filters and result state.
    Unifies the empty-state and filter-aware recommendations for both Content and Item catalogs.
    """
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
            if target_type == "content":
                trending_cat = get_popular_contents_cached(
                    section_id=section.id if section else None,
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
            else:
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
            if target_type == "content":
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
            else:
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

        elif intent_slugs and target_type == "content":
            trending_intent = get_popular_contents_cached(
                section_id=section.id if section else None,
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
            # No specific filter
            if target_type == "content" and section:
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
        # Empty state recovery recommendations (Zero Results)
        if category_slugs:
            if target_type == "content":
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
            else:
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
            # Global fallbacks for recovery
            if target_type == "content" and section:
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
