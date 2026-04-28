# app/integrations/content/newsapi.py
"""
NewsAPI.org fetcher — 100 requests/day free tier.
Get a free key at: https://newsapi.org/register
Env var: NEWS_API_KEY
"""
from authlib.oauth2.rfc6749.grants import resource_owner_password_credentials
import logging
import requests
from flask import current_app
from app.integrations.external.api import (
    can_call_newsapi, record_newsapi_call,
    should_refetch, mark_fetched,
)

from app.integrations.discovery import DiscoveryManager
from app.integrations.enrichment.pipeline import prepare_article

logger = logging.getLogger(__name__)


def fetch_section_category_newsapi(section_slug: str, category_slug: str, query_data: list[dict]) -> int:
    api_key = current_app.config.get("NEWS_API_KEY")
    if not api_key:
        logger.warning("[NewsAPI] NEWS_API_KEY not set — skipping")
        return 0

    stored = 0
    for q_obj in query_data:
        q_text = q_obj["query"]
        cache_key = f"newsapi:{category_slug}:{q_text}"
        
        if not should_refetch(section_slug, cache_key, hours=6):
            logger.debug("[NewsAPI] Skipping '%s' — fetched recently", q_text)
            continue

        if not can_call_newsapi():
            logger.warning("[NewsAPI] Daily limit reached — stopping")
            break

        try:
            print(f"  [NewsAPI] Searching: {q_text}...")
            logger.info(f"[NewsAPI] Query: {q_text}")

            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        q_text,
                    "language": "en",
                    "sortBy":   "publishedAt",
                    "pageSize": 80,
                    "apiKey":   api_key,
                },
                timeout=10,
            )
            resp.raise_for_status()
            record_newsapi_call()
            mark_fetched(
                section_slug, 
                cache_key, 
                category=category_slug, 
                source="newsapi", 
                normalized_query=q_text
            )

            from app.domains.content.ingestion import ingest_content
            from app.core.extensions import db
            query_stored = 0
            for raw in resp.json().get("articles", []):
                # 1. Enrichment/Classification
                raw = prepare_article(raw, section_slug, category_slug, q_obj)

                if ingest_content(db.session, object_type="article", raw_data=raw):
                    query_stored += 1
            
            stored += query_stored
            if query_stored > 0:
                print(f"    -> [NewsAPI] Stored {query_stored} new articles")
                    
        except Exception:
            logger.exception("[NewsAPI] Error fetching '%s' for %s", q_text, category_slug)

    return stored


def fetch_all_sections(limit: int | None = None) -> int:
    total = 0
    discovery = DiscoveryManager()
    queries_registry = discovery.get_queries_by_section(source_filter="newsapi")
    
    # Flatten the registry into a list of (section, category, q_obj)
    flat_queries = []
    for section, categories in queries_registry.items():
        for category, queries in categories.items():
            for q in queries:
                flat_queries.append((section, category, q))
    
    if not flat_queries:
        return 0

    # If limited, shuffle to get a diverse sample across sections/categories
    import random
    if limit:
        random.shuffle(flat_queries)
        flat_queries = flat_queries[:limit]

    logger.info("[NewsAPI] Starting discovery run with %d queries (Diverse Sample)", len(flat_queries))
    
    # Group back by section/category for efficient execution (optional, but cleaner logs)
    for section_slug, category_slug, q_obj in flat_queries:
        count = fetch_section_category_newsapi(section_slug, category_slug, [q_obj])
        total += count
        
    return total
