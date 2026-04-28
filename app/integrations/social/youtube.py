# app/integrations/social/youtube.py
"""
YouTube Data API v3 fetcher — specifically for the "reviews" section.
Quota: 10,000 units/day. 1 search = 100 units.
"""
import logging
import requests
from flask import current_app
from app.integrations.external.api import (
    can_call_youtube, record_youtube_call,
    should_refetch, mark_fetched
)

from app.integrations.discovery import DiscoveryManager
from app.integrations.enrichment.pipeline import prepare_article
logger = logging.getLogger(__name__)


def fetch_youtube_section_category(section_slug: str, category_slug: str, query_data: list[dict], region_code: str = "SA", results_per_query: int = 5) -> int:
    api_key = current_app.config.get("YOUTUBE_API_KEY")
    if not api_key:
        logger.warning("[YouTube] YOUTUBE_API_KEY not set — skipping")
        return 0

    stored = 0
    units_per_search = 100

    for q_obj in query_data:
        query = q_obj["query"]
        cache_key = f"youtube:{region_code}:{category_slug}:{query}"
        
        if not should_refetch(section_slug, cache_key, hours=12):
            continue

        if not can_call_youtube(units=units_per_search):
            logger.warning("[YouTube] Daily quota reached — stopping")
            break

        # Determine best YouTube category ID for the content
        video_category_id = "28" if "electronics" in category_slug.lower() else None

        try:
            print(f"  [YouTube] ({region_code}) Searching: {query}...") # TERMINAL FEEDBACK
            logger.info(f"[YouTube] Region: {region_code}, Query: {query}")

            params = {
                "part":             "snippet",
                "q":                query,
                "type":             "video",
                "relevanceLanguage":"ar" if any(c in query for c in 'ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي') else "en",
                "regionCode":       region_code,
                "order":            "relevance",
                "maxResults":       results_per_query,
                "key":              api_key,
            }
            if video_category_id:
                params["videoCategoryId"] = video_category_id

            resp = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
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

            from app.domains.content.ingestion import ingest_content
            from app.core.extensions import db

            # Ensure q_obj has the region for ingestion
            q_obj["region"] = region_code

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
                    "is_video":     True,
                    "region":       region_code
                }
                raw = prepare_article(raw, section_slug, category_slug, q_obj)
                
                raw["external_id"] = video_id
                if ingest_content(db.session, object_type="video", raw_data=raw):
                    stored += 1

        except Exception:
            logger.exception("[YouTube] Error for query: %s in %s", query, category_slug)

    return stored


def fetch_youtube_reviews(limit: int | None = None) -> int:
    total = 0
    discovery = DiscoveryManager()
    queries_registry = discovery.get_queries_by_section(source_filter="youtube")
    
    # Flatten into (section, category, q_obj, region)
    flat_tasks = []
    for region in ["SA", "AE"]:
        for section, categories in queries_registry.items():
            for category, queries in categories.items():
                for q in queries:
                    flat_tasks.append((section, category, q, region))

    if not flat_tasks:
        return 0

    import random
    if limit:
        random.shuffle(flat_tasks)
        flat_tasks = flat_tasks[:limit]
        print(f"--- Starting YouTube Discovery (Diverse Sample of {limit} queries) ---")

    for section, category, q_obj, region in flat_tasks:
        count = fetch_youtube_section_category(section, category, [q_obj], region_code=region)
        total += count
        
    return total
