import math
import re
from datetime import datetime, timezone



SEARCH_TYPES = ("all", "articles", "posts", "videos", "products")
CONTENT_INTENT_TERMS = {
    "how",
    "guide",
    "tutorial",
    "review",
    "tips",
    "what",
    "why",
    "news",
}
SHOPPING_INTENT_TERMS = {
    "buy",
    "best",
    "price",
    "compare",
    "top",
    "vs",
    "deal",
    "deals",
    "product",
    "products",
}
PRODUCT_HINT_TERMS = {
    "phone",
    "laptop",
    "camera",
    "headphones",
    "watch",
    "perfume",
    "tablet",
}

# Ranking weights stay intentionally small and readable. Text relevance is the
# base signal; popularity, freshness, and intent only adjust close matches.
TEXT_WEIGHT = 4.0
POPULARITY_WEIGHT = 0.8
FRESHNESS_WEIGHT = 0.6
INTENT_WEIGHT = 1.2


def normalize_search_query(query):
    return " ".join((query or "").strip().lower().split())


def tokenize_query(query):
    return re.findall(r"[a-z0-9]+", normalize_search_query(query))


def detect_search_intent(query):
    normalized = normalize_search_query(query)
    tokens = set(tokenize_query(normalized))

    content_score = sum(1 for term in CONTENT_INTENT_TERMS if term in tokens)
    shopping_score = sum(1 for term in SHOPPING_INTENT_TERMS if term in tokens)
    shopping_score += sum(1 for term in PRODUCT_HINT_TERMS if term in tokens)

    if "what is" in normalized or "how to" in normalized:
        content_score += 2
    if " vs " in f" {normalized} ":
        shopping_score += 2
        content_score += 1

    return {
        "content_score": content_score,
        "shopping_score": shopping_score,
    }


def _value(obj, key, default=""):
    if not obj:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _joined_names(values):
    return " ".join(str(_value(value, "name", "")) for value in (values or []))


def _text_relevance(query, result):
    terms = tokenize_query(query)
    if not terms:
        return 0.0

    target = result.get("target") or {}
    category = result.get("category") or {}
    brand = result.get("brand") or {}
    title = result.get("name") or _value(target, "title", "")
    slug = result.get("slug") or _value(category, "slug", "")
    primary = " ".join([str(title or ""), str(slug or "")]).lower()
    secondary = " ".join(
        [
            str(result.get("description") or ""),
            str(_value(target, "preview_text", "")),
            str(_value(target, "description", "")),
            str(_value(category, "name", "")),
            str(_value(brand, "name", "")),
            _joined_names(result.get("topics")),
            _joined_names(result.get("brands")),
        ]
    ).lower()

    score = 0.0
    phrase = normalize_search_query(query)
    if phrase and phrase in primary:
        score += 3.0
    if phrase and phrase in secondary:
        score += 1.5

    for term in terms:
        if term in primary:
            score += 1.2
        elif term in secondary:
            score += 0.6

    return score * TEXT_WEIGHT


def _freshness_score(result):
    raw_date = result.get("published_at") or result.get("created_at")
    if not raw_date:
        return 0.0

    if isinstance(raw_date, str):
        try:
            raw_date = datetime.fromisoformat(raw_date)
        except ValueError:
            return 0.0

    if raw_date.tzinfo is None:
        raw_date = raw_date.replace(tzinfo=timezone.utc)

    age_days = max((datetime.now(timezone.utc) - raw_date).days, 0)
    return FRESHNESS_WEIGHT / (1 + age_days / 30)


def _popularity_score(result):
    signals = [
        result.get("view_count") or 0,
        result.get("comment_count") or 0,
        result.get("review_count") or 0,
        result.get("click_count") or 0,
    ]
    target = result.get("target") or {}
    signals.append(_value(target, "upvotes", 0) or 0)
    return math.log1p(sum(signals)) * POPULARITY_WEIGHT


def _intent_score(result, intent):
    result_type = result.get("search_type")
    if result_type == "product":
        return intent["shopping_score"] * INTENT_WEIGHT
    return intent["content_score"] * INTENT_WEIGHT


def _attach_score(result, query, intent):
    scored = dict(result)
    scored["_search"] = {
        "score": (
            _text_relevance(query, scored)
            + _popularity_score(scored)
            + _freshness_score(scored)
            + _intent_score(scored, intent)
        ),
        "type": scored.get("search_type"),
    }
    return scored


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
        content_results.append(_attach_score(product, normalized_query, intent))

    product_results = []
    for product in get_search_items(normalized_query, limit=80):
        data = serialize_item(product)
        data["search_type"] = "product"
        product_results.append(_attach_score(data, normalized_query, intent))

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
    normalized_query = normalize_search_query(query)
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
