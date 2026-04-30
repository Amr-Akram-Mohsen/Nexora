# app/integrations/content/gnews.py
"""
GNews.io fetcher — 100 requests/day free tier.
Advantage: has country= filter (sa / ae) and lang=ar for regional data.
"""
import logging
import requests
from flask import current_app
from app.integrations.external.api import (
    can_call_gnews, record_gnews_call,
    should_refetch, mark_fetched,
)
from app.integrations.enrichment.pipeline import prepare_article
from app.integrations.discovery import DiscoveryManager
from app.integrations.exceptions import (
    PipelineFatalError, PipelineQuotaExceededError
)

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
            print(f"  [GNews] ({country}) Searching: {q_text}...")
            logger.info(f"[GNews] Country: {country}, Query: {q_text}")

            try:
                resp = requests.get(
                    "https://gnews.io/api/v4/search",
                    params={
                        "q":       q_text,
                        "lang":    "en" if not any(c in q_text for c in 'ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي') else "ar",
                        "country": country,
                        "max":     50,
                        "apikey":  api_key,
                    },
                    timeout=10,
                )
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                if resp is not None and resp.status_code == 403:
                    logger.error("[GNews] Quota exceeded or Access Denied")
                    raise PipelineQuotaExceededError("GNews Quota Exceeded")
                logger.warning("[GNews] API request failed for query '%s': %s", q_text, str(e))
                continue

            record_gnews_call()
            mark_fetched(
                section_slug, 
                cache_key, 
                category=category_slug, 
                source="gnews", 
                normalized_query=q_text
            )
            
            from app.domains.content.ingestion import ingest_content
            from app.core.extensions import db

            query_stored = 0
            for raw in resp.json().get("articles", []):
                raw["image_url"] = raw.get("image")
                raw["region"] = country.upper()

                # 1. Enrichment/Classification
                # Update q_obj to include region
                q_obj["region"] = country.upper()
                raw = prepare_article(raw, section_slug, category_slug, q_obj)                

                try:
                    if ingest_content(db.session, object_type="article", raw_data=raw):
                        query_stored += 1
                except Exception as e:
                    logger.critical("[GNews] FATAL: Database insertion failed. Pipeline stopping.")
                    raise PipelineFatalError(f"Database insertion failed: {str(e)}") from e
            
            stored += query_stored
            if query_stored > 0:
                print(f"    -> [GNews] Stored {query_stored} new articles")

        except (PipelineFatalError, PipelineQuotaExceededError):
            raise
        except Exception:
            logger.exception("[GNews] Unexpected error for '%s' (%s)", q_text, country)

    return stored


def fetch_all_gnews(limit: int | None = None) -> int:
    total = 0
    discovery = DiscoveryManager()
    queries_registry = discovery.get_queries_by_section(source_filter="gnews")
    
    # Flatten into (section, category, q_obj, country)
    flat_tasks = []
    for section, categories in queries_registry.items():
        for category, queries in categories.items():
            for q in queries:
                for country in TARGET_COUNTRIES:
                    flat_tasks.append((section, category, q, country))

    if not flat_tasks:
        return 0

    import random
    if limit:
        random.shuffle(flat_tasks)
        flat_tasks = flat_tasks[:limit]

    logger.info("[GNews] Starting discovery run with %d tasks (Diverse Sample)", len(flat_tasks))

    for section, category, q_obj, country in flat_tasks:
        count = fetch_gnews_section_category(section, category, [q_obj], country)
        total += count
        
    return total
