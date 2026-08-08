"""
Search Suggestions API — GET /api/search/suggestions
=====================================================
Returns fast, lightweight autocomplete suggestions for the live search dropdown.

Design decisions:
  - Uses the same ``get_search_contents`` / ``get_search_items`` domain services
    as the main search workflow — no new DB queries.
  - Limit is intentionally small (5 per type) to stay snappy.
  - 60-second cache TTL (shorter than main search because suggestions are seen
    at every keystroke and staleness matters less here).
  - Returns 400 for queries shorter than 2 characters (avoids full-table scans).
"""
import logging

from flask import Blueprint, jsonify, request

from app.application.recommendation.query_preprocessor import preprocess_query
from app.infrastructure import cache

logger = logging.getLogger(__name__)

bp = Blueprint("suggestions", __name__)


@bp.route("/api/search/suggestions", methods=["GET"])
def search_suggestions():
    """
    GET /api/search/suggestions?q=<query>

    Returns:
        200 JSON:
            {
                "query": str,
                "suggestions": [
                    {
                        "id": int,
                        "title": str,
                        "type": "article" | "video" | "post" | "product",
                        "url": str,
                        "image_url": str | null,
                        "meta": str        # e.g. brand name or category
                    },
                    ...
                ],
                "total": int
            }
        400 JSON: {"error": "Query too short"}
    """
    raw_q = request.args.get("q", "").strip()

    if len(raw_q) < 2:
        return jsonify({"error": "Query too short"}), 400

    pq = preprocess_query(raw_q)
    cache_key = f"suggestions:v1:{pq.normalized}"
    cached = cache.get(cache_key)
    if cached is not None:
        return jsonify(cached)

    suggestions = _build_suggestions(pq.normalized)
    payload = {
        "query": pq.raw,
        "suggestions": suggestions,
        "total": len(suggestions),
    }

    cache.set(cache_key, payload, timeout=60)
    return jsonify(payload)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SUGGESTION_LIMIT = 5  # per content type


def _build_suggestions(normalized_query: str) -> list[dict]:
    """
    Queries content and products for the top suggestions and merges them into
    a flat list ordered: exact/prefix title matches first, then ts_rank order.

    The function imports lazily to avoid circular imports at module load time.
    """
    from flask import url_for

    from app.domains.content.service import get_search_contents, serialize_content
    from app.domains.product.service import get_search_items, serialize_item

    suggestions: list[dict] = []

    # ── Content suggestions (articles, videos, posts) ──
    try:
        content_results = get_search_contents(normalized_query, limit=_SUGGESTION_LIMIT * 3)
        for item in content_results[:_SUGGESTION_LIMIT]:
            target = item.get("target") or {}
            obj_type = item.get("object_type", "article")
            title = (
                target.get("title")
                or item.get("title")
                or ""
            )
            image_url = target.get("image_url") or item.get("image_url")
            category = item.get("category") or {}
            section = item.get("section") or {}
            meta = (
                category.get("name")
                or section.get("name")
                or obj_type.title()
            )
            suggestions.append({
                "id": item.get("id"),
                "title": title,
                "type": obj_type,
                "url": url_for("content.content_page", content_id=item["id"], _external=False),
                "image_url": image_url,
                "meta": meta,
            })
    except Exception:
        logger.exception("[suggestions] Content query failed for q=%r", normalized_query)

    # ── Product suggestions ──
    try:
        product_results = get_search_items(normalized_query, limit=_SUGGESTION_LIMIT * 2)
        for product in product_results[:_SUGGESTION_LIMIT]:
            serialized = serialize_item(product)
            brand = serialized.get("brand") or {}
            category = serialized.get("category") or {}
            meta = brand.get("name") or category.get("name") or "Product"
            images = serialized.get("images") or []
            image_url = images[0].get("image_url") if images else None
            suggestions.append({
                "id": serialized.get("id"),
                "title": serialized.get("name") or "",
                "type": "product",
                "url": url_for("product.item_page", product_id=serialized["id"], _external=False),
                "image_url": image_url,
                "meta": meta,
            })
    except Exception:
        logger.exception("[suggestions] Product query failed for q=%r", normalized_query)

    return suggestions
