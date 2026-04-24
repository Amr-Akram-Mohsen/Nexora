# app/integrations/content/newsapi.py
"""
NewsAPI.org fetcher — 100 requests/day free tier.
Get a free key at: https://newsapi.org/register
Env var: NEWS_API_KEY
"""
import logging
import requests
from flask import current_app
from app.integrations.cleaner import clean_article_data
from app.domains.article.ingestion import store_article
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
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        q_text,
                    "language": "en",
                    "sortBy":   "publishedAt",
                    "pageSize": 15,
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

            for raw in resp.json().get("articles", []):
                raw = prepare_article(raw, section_slug, category_slug, q_obj)
                                                
                cleaned = clean_article_data(raw)
                if cleaned and store_article(cleaned):
                    stored += 1

        except Exception:
            logger.exception("[NewsAPI] Error fetching '%s' for %s", q_text, category_slug)

    return stored


def fetch_all_sections() -> int:
    total = 0
    discovery = DiscoveryManager()
    queries_registry = discovery.get_queries_by_section()
    
    for section_slug, categories in queries_registry.items():
        logger.info("[NewsAPI] Fetching Section: %s", section_slug)
        for category_slug, queries in categories.items():
            logger.info("[NewsAPI]   Category: %s (%d queries)", category_slug, len(queries))
            count = fetch_section_category_newsapi(section_slug, category_slug, queries)
            total += count
            logger.info("[NewsAPI]     -> %d new articles stored", count)
    return total
