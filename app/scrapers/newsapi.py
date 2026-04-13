# app/scrapers/newsapi.py
"""
NewsAPI.org fetcher — 100 requests/day free tier.
Get a free key at: https://newsapi.org/register
Env var: NEWS_API_KEY
"""
import logging
import requests
from flask import current_app
from .cleaner import clean_article_data
from .storer import store_article
from app.services.api_service import (
    can_call_newsapi, record_newsapi_call,
    should_refetch, mark_fetched,
)

logger = logging.getLogger(__name__)

# ── Query Registry ────────────────────────────────────────────────
# Mapped by [Section] -> [Category] -> [List of Queries]
SECTION_QUERIES = {
    "news": {
        "electronics": [
            "tech news", "AI news", "smartphone news", "gadget release",
            "semiconductor news", "wearable tech", "consumer electronics"
        ],
        "perfumes": [
            "perfume launch", "fragrance news", "perfume brand",
            "niche fragrance", "cologne release", "designer perfume"
        ],
        "accessories": [
            "luxury watch news", "fashion accessories", "designer brand",
            "jewelry trends", "smartwatch features", "sunglasses fashion"
        ],
    },
    "reviews": {
        "electronics": [
            "smartphone review", "laptop review", "tablet review",
            "smartwatch review", "headphones review", "camera review"
        ],
        "perfumes": [
            "perfume review", "fragrance review", "cologne review",
            "scent review", "best perfumes"
        ],
        "accessories": [
            "watch review", "sunglasses review", "luxury accessories review",
            "handbag review", "wallet review"
        ],
    },
    "tutorials": {
        "electronics": [
            "tech tutorial", "how to programming", "smartphone tips",
            "laptop setup guide", "software tutorial"
        ],
        "accessories": [
            "how to style accessories", "fashion tips", "watch maintenance",
            "jewelry care"
        ],
    },
    "trends": {
        "electronics": [
            "technology trends 2025", "future of smartphones", "AI trends",
            "smart home trends"
        ],
        "perfumes": [
            "fragrance trends 2025", "best perfumes 2025", "perfume ingredients",
            "sustainable fragrances"
        ],
        "accessories": [
            "fashion trends 2025", "luxury trends", "watch trends 2025",
            "jewelry trends 2025"
        ],
    },
}


def fetch_section_category_newsapi(section_slug: str, category_slug: str, queries: list[str]) -> int:
    api_key = current_app.config.get("NEWS_API_KEY")
    if not api_key:
        logger.warning("[NewsAPI] NEWS_API_KEY not set — skipping")
        return 0

    stored = 0
    for q in queries:
        if not should_refetch(section_slug, f"newsapi:{category_slug}:{q}", hours=6):
            logger.debug("[NewsAPI] Skipping '%s' — fetched recently", q)
            continue

        if not can_call_newsapi():
            logger.warning("[NewsAPI] Daily limit reached — stopping")
            break

        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        q,
                    "language": "en",
                    "sortBy":   "publishedAt",
                    "pageSize": 15,
                    "apiKey":   api_key,
                },
                timeout=10,
            )
            resp.raise_for_status()
            record_newsapi_call()
            mark_fetched(section_slug, f"newsapi:{category_slug}:{q}")

            for raw in resp.json().get("articles", []):
                raw["section_slug"] = section_slug
                raw["category_slug"] = category_slug
                cleaned = clean_article_data(raw, section_slug)
                if cleaned and store_article(cleaned):
                    stored += 1

        except Exception:
            logger.exception("[NewsAPI] Error fetching '%s' for %s", q, category_slug)

    return stored


def fetch_all_sections() -> int:
    total = 0
    for section_slug, categories in SECTION_QUERIES.items():
        logger.info("[NewsAPI] Fetching Section: %s", section_slug)
        for category_slug, queries in categories.items():
            logger.info("[NewsAPI]   Category: %s (%d queries)", category_slug, len(queries))
            count = fetch_section_category_newsapi(section_slug, category_slug, queries)
            total += count
            logger.info("[NewsAPI]     -> %d new articles stored", count)
    return total
