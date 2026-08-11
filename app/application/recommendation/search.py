import math
import re
from datetime import datetime, timezone
SEARCH_TYPES = ('all', 'articles', 'posts', 'videos', 'products')
from app.domains.recommendation.service.search_scoring import detect_search_intent, attach_score
def get_unified_search_results_cached(normalized_query):
    from app.infrastructure import cache
    from app.domains.content.service import get_search_contents
    from app.domains.product.service import get_search_items, serialize_item
    cache_key = f'search:unified:v1:{normalized_query}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    intent = detect_search_intent(normalized_query)
    content_results = []
    for content in get_search_contents(normalized_query, limit=80):
        product = dict(content)
        product['search_type'] = product.get('object_type')
        content_results.append(attach_score(product, normalized_query, intent))
    product_results = []
    for product in get_search_items(normalized_query, limit=80):
        data = serialize_item(product)
        data['search_type'] = 'product'
        product_results.append(attach_score(data, normalized_query, intent))
    results = sorted(content_results + product_results, key=lambda row: row.get('_search', {}).get('score', 0), reverse=True)
    cache.set(cache_key, results, timeout=120)
    return results
def _filter_results(results, result_type):
    match result_type:
        case 'all':
            return results
        case 'articles':
            return [row for row in results if row.get('search_type') == 'article']
        case 'posts':
            return [row for row in results if row.get('search_type') == 'post']
        case 'videos':
            return [row for row in results if row.get('search_type') == 'video']
        case 'products':
            return [row for row in results if row.get('search_type') == 'product']
        case _:
            return results
def build_result_counts(results):
    return {'all': len(results), 'articles': sum((1 for row in results if row.get('search_type') == 'article')), 'posts': sum((1 for row in results if row.get('search_type') == 'post')), 'videos': sum((1 for row in results if row.get('search_type') == 'video')), 'products': sum((1 for row in results if row.get('search_type') == 'product'))}
def build_grouped_results(results: list[dict]) -> dict:
    grouped: dict[str, list] = {'products': [], 'articles': [], 'videos': [], 'posts': []}
    for row in results:
        match row.get('search_type'):
            case 'product':
                grouped['products'].append(row)
            case 'article':
                grouped['articles'].append(row)
            case 'video':
                grouped['videos'].append(row)
            case 'post':
                grouped['posts'].append(row)
    return grouped
def search_workflow(query, result_type='all'):
    normalized_query = ' '.join((query or '').strip().lower().split())
    active_type = result_type if result_type in SEARCH_TYPES else 'all'
    if not normalized_query:
        results = []
    else:
        results = list(get_unified_search_results_cached(normalized_query))
    filtered = _filter_results(results, active_type)
    grouped_results = build_grouped_results(results) if active_type == 'all' else None
    return {'query': query.strip() if query else '', 'normalized_query': normalized_query, 'active_type': active_type, 'results': filtered, 'grouped_results': grouped_results, 'result_counts': build_result_counts(results), 'intent': detect_search_intent(normalized_query), 'search_types': SEARCH_TYPES}