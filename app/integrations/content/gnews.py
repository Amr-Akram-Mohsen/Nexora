# app/scrapers/gnews_fetcher.py
"""
GNews.io fetcher — 100 requests/day free tier.
Advantage: has country= filter (sa / ae) and lang=ar for regional data.
"""
import logging
import requests
from flask import current_app
from app.integrations.cleaner import clean_article_data
from app.domains.article.storage import store_article
from app.integrations.external.api import (
    can_call_gnews, record_gnews_call,
    should_refetch, mark_fetched,
)

logger = logging.getLogger(__name__)

# ── Query Registry ────────────────────────────────────────────────
# Mapped by [Section] -> [Category] -> [List of Queries]
SECTION_QUERIES = {
    "news": {
        "electronics": [
            "technology", "smartphones", "artificial intelligence", "tech news",
            "أخبار التقنية", "هواتف ذكية", "الذكاء الاصطناعي", "أجهزة ذكية"
        ],
        "perfumes": [
            "عطر رجالي", "عطر نسائي", "oud perfume", "perfume news",
            "عطور فخمة", "أخبار العطور", "أفضل عطر", "fragrance release"
        ],
        "accessories": [
            "luxury watch news", "fashion accessories", "designer brand",
            "ساعات فاخرة", "مجوهرات", "نظارات شمسية", "إكسسوارات الموضة"
        ],
    },
    "reviews": {
        "electronics": [
            "smartphone review", "laptop review", "tablet review",
            "مراجعة هاتف", "مراجعة لابتوب", "تقييم أجهزة", "headphones review"
        ],
        "perfumes": [
            "perfume review", "fragrance review", "مراجعة عطر",
            "تقييم عطور", "best colognes", "عطور الصيف"
        ],
        "accessories": [
            "watch review", "sunglasses review", "luxury accessories review",
            "مراجعة ساعة", "أفضل الإكسسوارات"
        ],
    },
}

TARGET_COUNTRIES = ["sa", "ae"]


def fetch_gnews_section_category(section_slug: str, category_slug: str, queries: list[str], country: str) -> int:
    api_key = current_app.config.get("GNEWS_API_KEY")
    if not api_key:
        logger.warning("[GNews] GNEWS_API_KEY not set — skipping")
        return 0

    stored = 0
    for q in queries:
        cache_key = f"gnews:{country}:{category_slug}:{q}"
        if not should_refetch(section_slug, cache_key, hours=8):
            continue

        if not can_call_gnews():
            logger.warning("[GNews] Daily limit reached")
            break

        try:
            resp = requests.get(
                "https://gnews.io/api/v4/search",
                params={
                    "q":       q,
                    "lang":    "en" if not any(c in q for c in 'ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي') else "ar",
                    "country": country,
                    "max":     10,
                    "apikey":  api_key,
                },
                timeout=10,
            )
            resp.raise_for_status()
            record_gnews_call()
            mark_fetched(section_slug, cache_key)

            for raw in resp.json().get("articles", []):
                raw["image_url"] = raw.get("image")
                raw["section_slug"] = section_slug
                raw["category_slug"] = category_slug
                cleaned = clean_article_data(raw, section_slug)
                if cleaned and store_article(cleaned):
                    stored += 1

        except Exception:
            logger.exception("[GNews] Error for '%s' (%s) in %s", q, country, category_slug)

    return stored


def fetch_all_gnews() -> int:
    total = 0
    for section_slug, categories in SECTION_QUERIES.items():
        logger.info("[GNews] Fetching Section: %s", section_slug)
        for category_slug, queries in categories.items():
            for country in TARGET_COUNTRIES:
                logger.info("[GNews]   Country: %s, Category: %s (%d queries)", country, category_slug, len(queries))
                count = fetch_gnews_section_category(section_slug, category_slug, queries, country)
                total += count
                logger.info("[GNews]     -> %d new articles stored", count)
    return total
