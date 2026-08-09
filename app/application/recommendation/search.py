import math
import re
from datetime import datetime, timezone



SEARCH_TYPES = ("all", "articles", "posts", "videos", "products")
from app.domains.recommendation.service.search_scoring import detect_search_intent, attach_score


def get_unified_search_results_cached(normalized_query):
    from app.infrastructure import cache
    from app.domains.content.service import get_search_contents
    from app.domains.product.service import get_search_items, serialize_item

    cache_key = f"search:unified:v1:{normalized_query}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    intent = detect_search_intent(normalized_query)

    content_results = []
    for content in get_search_contents(normalized_query, limit=80):
        product = dict(content)
        product["search_type"] = product.get("object_type")
        content_results.append(attach_score(product, normalized_query, intent))

    product_results = []
    for product in get_search_items(normalized_query, limit=80):
        data = serialize_item(product)
        data["search_type"] = "product"
        product_results.append(attach_score(data, normalized_query, intent))

    results = sorted(
        content_results + product_results,
        key=lambda row: row.get("_search", {}).get("score", 0),
        reverse=True,
    )
    cache.set(cache_key, results, timeout=120)
    return results


def _filter_results(results, result_type):
    if result_type == "all":
        return results
    if result_type == "articles":
        return [row for row in results if row.get("search_type") == "article"]
    if result_type == "posts":
        return [row for row in results if row.get("search_type") == "post"]
    if result_type == "videos":
        return [row for row in results if row.get("search_type") == "video"]
    if result_type == "products":
        return [row for row in results if row.get("search_type") == "product"]
    return results


def build_result_counts(results):
    return {
        "all": len(results),
        "articles": sum(1 for row in results if row.get("search_type") == "article"),
        "posts": sum(1 for row in results if row.get("search_type") == "post"),
        "videos": sum(1 for row in results if row.get("search_type") == "video"),
        "products": sum(1 for row in results if row.get("search_type") == "product"),
    }


def build_grouped_results(results: list[dict]) -> dict:
    """
    Partition a flat scored results list into content-type buckets.

    Used by the template when ``active_type == 'all'`` to render
    grouped sections (Products / Articles / Videos / Posts) instead
    of a single interleaved list.

    Returns a dict with:
        products   – list of product results
        articles   – list of article results
        videos     – list of video results
        posts      – list of post results
    Each bucket is already in score-descending order (inherited from
    the sorted ``results`` list).
    """
    grouped: dict[str, list] = {
        "products": [],
        "articles": [],
        "videos": [],
        "posts": [],
    }
    for row in results:
        t = row.get("search_type")
        if t == "product":
            grouped["products"].append(row)
        elif t == "article":
            grouped["articles"].append(row)
        elif t == "video":
            grouped["videos"].append(row)
        elif t == "post":
            grouped["posts"].append(row)
    return grouped

def search_workflow(query, result_type="all"):
    normalized_query = " ".join((query or "").strip().lower().split())
    active_type = result_type if result_type in SEARCH_TYPES else "all"

    if not normalized_query:
        results = []
    else:
        results = list(get_unified_search_results_cached(normalized_query))

    filtered = _filter_results(results, active_type)
    grouped_results = build_grouped_results(results) if active_type == "all" else None

    return {
        "query": query.strip() if query else "",
        "normalized_query": normalized_query,
        "active_type": active_type,
        "results": filtered,
        "grouped_results": grouped_results,
        "result_counts": build_result_counts(results),
        "intent": detect_search_intent(normalized_query),
        "search_types": SEARCH_TYPES,
    }
