# app/scrapers/gnews_fetcher.py
"""
GNews.io fetcher — 100 requests/day free tier.
Advantage: has country= filter (sa / ae) and lang=ar for regional data.
"""
import logging
import requests
from flask import current_app
from app.integrations.cleaner import clean_article_data
from app.domains.article.ingestion import store_article
from app.integrations.external.api import (
    can_call_gnews, record_gnews_call,
    should_refetch, mark_fetched,
)

from app.integrations.discovery import DiscoveryManager

logger = logging.getLogger(__name__)

TARGET_COUNTRIES = ["sa", "ae"]


def fetch_gnews_section_category(section_slug: str, category_slug: str, query_data: list[dict], country: str) -> int:
    api_key = current_app.config.get("GNEWS_API_KEY")
    if not api_key:
        logger.warning("[GNews] GNEWS_API_KEY not set — skipping")
        return 0

    stored = 0
    for q_obj in query_data:
        q_text = q_obj["query"]
        cache_key = f"gnews:{country}:{category_slug}:{q_text}"
        
        if not should_refetch(section_slug, cache_key, hours=8):
            continue

        if not can_call_gnews():
            logger.warning("[GNews] Daily limit reached")
            break

        try:
            resp = requests.get(
                "https://gnews.io/api/v4/search",
                params={
                    "q":       q_text,
                    "lang":    "en" if not any(c in q_text for c in 'ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي') else "ar",
                    "country": country,
                    "max":     10,
                    "apikey":  api_key,
                },
                timeout=10,
            )
            resp.raise_for_status()
            record_gnews_call()
            mark_fetched(
                section_slug, 
                cache_key, 
                category=category_slug, 
                source="gnews", 
                normalized_query=q_text
            )

            for raw in resp.json().get("articles", []):
                raw["image_url"] = raw.get("image")
                raw["section_slug"] = section_slug
                raw["category_slug"] = category_slug
                raw["topic_slugs"] = q_obj.get("topics", [])
                raw["brand_names"] = q_obj.get("brands", [])
                
                cleaned = clean_article_data(raw)
                if cleaned and store_article(cleaned):
                    stored += 1

        except Exception:
            logger.exception("[GNews] Error for '%s' (%s) in %s", q_text, country, category_slug)

    return stored


def fetch_all_gnews() -> int:
    total = 0
    discovery = DiscoveryManager()
    queries_registry = discovery.get_queries_by_section()
    
    # GNews is mainly for news and reviews
    for section_slug in ["news", "reviews"]:
        if section_slug not in queries_registry:
            continue
            
        categories = queries_registry[section_slug]
        logger.info("[GNews] Fetching Section: %s", section_slug)
        for category_slug, queries in categories.items():
            for country in TARGET_COUNTRIES:
                logger.info("[GNews]   Country: %s, Category: %s (%d queries)", country, category_slug, len(queries))
                count = fetch_gnews_section_category(section_slug, category_slug, queries, country)
                total += count
                logger.info("[GNews]     -> %d new articles stored", count)
    return total
