# app/scrapers/youtube_fetcher.py
"""
YouTube Data API v3 fetcher — specifically for the "reviews" section.
Quota: 10,000 units/day. 1 search = 100 units.
"""
import logging
import requests
from flask import current_app
from app.integrations.cleaner import clean_article_data
from app.domains.article.ingestion import store_article
from app.integrations.external.api import (
    can_call_youtube, record_youtube_call,
    should_refetch, mark_fetched
)

from app.integrations.discovery import DiscoveryManager

logger = logging.getLogger(__name__)


def fetch_youtube_section_category(section_slug: str, category_slug: str, query_data: list[dict], results_per_query: int = 5) -> int:
    api_key = current_app.config.get("YOUTUBE_API_KEY")
    if not api_key:
        logger.warning("[YouTube] YOUTUBE_API_KEY not set — skipping")
        return 0

    stored = 0
    units_per_search = 100

    for q_obj in query_data:
        query = q_obj["query"]
        cache_key = f"youtube:{category_slug}:{query}"
        
        if not should_refetch(section_slug, cache_key, hours=12):
            logger.debug("[YouTube] Skipping '%s' — fetched recently", query)
            continue

        if not can_call_youtube(units=units_per_search):
            logger.warning("[YouTube] Daily quota reached — stopping")
            break

        try:
            resp = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part":             "snippet",
                    "q":                query,
                    "type":             "video",
                    "videoCategoryId":  "28",       # Science & Technology (works for frag/watch reviews too)
                    "relevanceLanguage":"ar" if any(c in query for c in 'ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي') else "en",
                    "regionCode":       "SA",        # Saudi region
                    "order":            "date",
                    "maxResults":       results_per_query,
                    "key":              api_key,
                },
                timeout=10,
            )
            resp.raise_for_status()
            record_youtube_call(units=units_per_search)
            mark_fetched(
                section_slug, 
                cache_key, 
                category=category_slug, 
                source="youtube", 
                normalized_query=query
            )

            for item in resp.json().get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if not video_id:
                    continue
                snippet = item.get("snippet", {})
                raw = {
                    "title":        snippet.get("title", ""),
                    "description":  snippet.get("description", ""),
                    "url":          f"https://www.youtube.com/watch?v={video_id}",
                    "image_url":    snippet.get("thumbnails", {}).get("high", {}).get("url"),
                    "published_at": snippet.get("publishedAt"),
                    "source_name":  snippet.get("channelTitle", ""),
                    "section_slug": section_slug,
                    "category_slug": category_slug,
                    "topic_slugs":  q_obj.get("topics", []),
                    "brand_names":  q_obj.get("brands", []),
                }
                cleaned = clean_article_data(raw)
                if cleaned and store_article(cleaned):
                    stored += 1

        except Exception:
            logger.exception("[YouTube] Error for query: %s in %s", query, category_slug)

    return stored


def fetch_youtube_reviews() -> int:
    total = 0
    section_slug = "reviews"
    discovery = DiscoveryManager()
    queries_registry = discovery.get_queries_by_section()
    
    categories = queries_registry.get(section_slug, {})
    
    for category_slug, queries in categories.items():
        logger.info("[YouTube] Fetching Section: %s, Category: %s (%d queries)", section_slug, category_slug, len(queries))
        count = fetch_youtube_section_category(section_slug, category_slug, queries)
        total += count
        logger.info("[YouTube]     -> %d new articles stored", count)
    return total
