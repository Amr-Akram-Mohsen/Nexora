from app.domains.content.service.query.trending import get_popular_contents as get_popular_contents_cached
from app.domains.product.service.search import get_popular_items as get_popular_items_cached

def get_contextual_recommendations(active_filters, has_results, section=None, target_type='content'):
    category_slugs = active_filters.get('category', [])
    brand_slugs = active_filters.get('brand', [])
    intent_slugs = active_filters.get('intent', [])
    blocks = []
    cat_name = category_slugs[0].replace('-', ' ').title() if category_slugs else ''
    brand_name = brand_slugs[0].replace('-', ' ').title() if brand_slugs else ''
    intent_name = intent_slugs[0].replace('-', ' ').title() if intent_slugs else ''
    if has_results:
        if category_slugs:
            if target_type == 'content':
                trending_cat = get_popular_contents_cached(section_id=section.id if section else None, category_slugs=tuple(category_slugs), limit=6)
                if trending_cat:
                    blocks.append({'title': f'Trending {cat_name} Content', 'type': 'content', 'products': trending_cat})
                cat_reviews = get_popular_contents_cached(category_slugs=tuple(category_slugs), intent_slugs=('review',), limit=6)
                if cat_reviews:
                    blocks.append({'title': f'Popular {cat_name} Reviews', 'type': 'content', 'products': cat_reviews})
                cat_guides = get_popular_contents_cached(category_slugs=tuple(category_slugs), intent_slugs=('buying-guide',), limit=6)
                if cat_guides:
                    blocks.append({'title': f'Related Buying Guides', 'type': 'content', 'products': cat_guides})
            else:
                cat_contents = get_popular_contents_cached(category_slugs=tuple(category_slugs), limit=6)
                if cat_contents:
                    blocks.append({'title': f'Trending {cat_name} Content', 'type': 'content', 'products': cat_contents})
                cat_products = get_popular_items_cached(category_slugs=tuple(category_slugs), limit=6)
                if cat_products:
                    blocks.append({'title': f'Popular {cat_name} Products', 'type': 'commercial', 'products': cat_products})
        elif brand_slugs:
            if target_type == 'content':
                brand_products = get_popular_items_cached(brand_slugs=tuple(brand_slugs), limit=6)
                if brand_products:
                    blocks.append({'title': f'Popular {brand_name} Products', 'type': 'commercial', 'products': brand_products})
                brand_reviews = get_popular_contents_cached(brand_slugs=tuple(brand_slugs), intent_slugs=('review',), limit=6)
                if brand_reviews:
                    blocks.append({'title': f'Related {brand_name} Reviews', 'type': 'content', 'products': brand_reviews})
                brand_guides = get_popular_contents_cached(brand_slugs=tuple(brand_slugs), intent_slugs=('buying-guide',), limit=6)
                if brand_guides:
                    blocks.append({'title': f'Related Buying Guides', 'type': 'content', 'products': brand_guides})
            else:
                brand_contents = get_popular_contents_cached(brand_slugs=tuple(brand_slugs), limit=6)
                if brand_contents:
                    blocks.append({'title': f'Trending {brand_name} Content', 'type': 'content', 'products': brand_contents})
                brand_products = get_popular_items_cached(brand_slugs=tuple(brand_slugs), limit=6)
                if brand_products:
                    blocks.append({'title': f'Popular {brand_name} Products', 'type': 'commercial', 'products': brand_products})
        elif intent_slugs and target_type == 'content':
            trending_intent = get_popular_contents_cached(section_id=section.id if section else None, intent_slugs=tuple(intent_slugs), limit=6)
            if trending_intent:
                blocks.append({'title': f'Trending {intent_name}s', 'type': 'content', 'products': trending_intent})
            popular_intent = get_popular_contents_cached(intent_slugs=tuple(intent_slugs), limit=6)
            if popular_intent:
                blocks.append({'title': f'Popular {intent_name}s', 'type': 'content', 'products': popular_intent})
        elif target_type == 'content' and section:
            trending_section = get_popular_contents_cached(section_id=section.id, limit=6)
            if trending_section:
                blocks.append({'title': f'Trending in {section.name}', 'type': 'content', 'products': trending_section})
        else:
            trending_products = get_popular_items_cached(limit=6)
            if trending_products:
                blocks.append({'title': 'Trending Products', 'type': 'commercial', 'products': trending_products})
            trending_reviews = get_popular_contents_cached(intent_slugs=('review',), limit=6)
            if trending_reviews:
                blocks.append({'title': 'Trending Reviews', 'type': 'content', 'products': trending_reviews})
    elif category_slugs:
        if target_type == 'content':
            cat_alternatives = get_popular_contents_cached(category_slugs=tuple(category_slugs), limit=6)
            if cat_alternatives:
                blocks.append({'title': f'Popular Alternatives in {cat_name}', 'type': 'content', 'products': cat_alternatives})
            cat_products = get_popular_items_cached(category_slugs=tuple(category_slugs), limit=6)
            if cat_products:
                blocks.append({'title': f'Popular Products in {cat_name}', 'type': 'commercial', 'products': cat_products})
        else:
            cat_alternatives = get_popular_items_cached(category_slugs=tuple(category_slugs), limit=6)
            if cat_alternatives:
                blocks.append({'title': f'Popular Alternatives in {cat_name}', 'type': 'commercial', 'products': cat_alternatives})
            cat_content = get_popular_contents_cached(category_slugs=tuple(category_slugs), limit=6)
            if cat_content:
                blocks.append({'title': f'Trending {cat_name} Content', 'type': 'content', 'products': cat_content})
    elif brand_slugs:
        brand_products = get_popular_items_cached(brand_slugs=tuple(brand_slugs), limit=6)
        if brand_products:
            blocks.append({'title': f'Popular {brand_name} Products', 'type': 'commercial', 'products': brand_products})
        brand_content = get_popular_contents_cached(brand_slugs=tuple(brand_slugs), limit=6)
        if brand_content:
            blocks.append({'title': f'Trending {brand_name} Content', 'type': 'content', 'products': brand_content})
    elif target_type == 'content' and section:
        trending_content = get_popular_contents_cached(section_id=section.id, limit=6)
        if trending_content:
            blocks.append({'title': 'Trending Content', 'type': 'content', 'products': trending_content})
        popular_products = get_popular_items_cached(limit=6)
        if popular_products:
            blocks.append({'title': 'Popular Products', 'type': 'commercial', 'products': popular_products})
    else:
        trending_products = get_popular_items_cached(limit=6)
        if trending_products:
            blocks.append({'title': 'Trending Products', 'type': 'commercial', 'products': trending_products})
        trending_reviews = get_popular_contents_cached(intent_slugs=('review',), limit=6)
        if trending_reviews:
            blocks.append({'title': 'Trending Reviews', 'type': 'content', 'products': trending_reviews})
    return blocks