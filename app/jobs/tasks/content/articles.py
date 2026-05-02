# app/jobs/tasks/content/articles.py
"""
Orchestrates all scraper/discovery jobs.
Balanced discovery across Electronics, Perfumes, and Accessories.
Fails gracefully if API keys are missing.
"""
import logging
from flask import current_app

logger = logging.getLogger(__name__)

from app.application.content.ingestion_workflow import run_orchestrated_ingestion
from app.application.content.ingestion.services import (
    DiscoveryService, EnrichmentService, NewsApiQuotaService, 
    GNewsQuotaService, GenericQuotaService, CooldownService
)
from app.core.extensions import db

def run_newsapi_fetch(limit: int | None = None):
    """Fetch from NewsAPI (tech/fragrance/fashion)."""
    if not current_app.config.get("NEWS_API_KEY"):
        logger.warning("[NewsAPI] Key missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.content.newsapi import fetch_newsapi_query
        
        logger.info("[Runner] Starting NewsAPI...")
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="NewsAPI",
            object_type="article",
            fetcher_func=fetch_newsapi_query,
            quota_service=NewsApiQuotaService(),
            enrichment_service=EnrichmentService(),
            discovery_service=DiscoveryService(),
            cooldown_service=CooldownService(),
            source_filter="newsapi",
            limit=limit,
            cooldown_hours=6
        )
        logger.info(f"[Runner] NewsAPI success — {count} stored")
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
        if isinstance(e, PipelineFatalError):
            logger.critical("[Runner] NewsAPI fetch ABORTED: %s", str(e))
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            logger.warning("[Runner] NewsAPI quota exceeded: %s", str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        logger.exception("[Runner] NewsAPI fetch failed")
        return {"status": "error", "error": str(e)}

def run_gnews_fetch(limit: int | None = None):
    """Fetch from GNews (regional/global)."""
    if not current_app.config.get("GNEWS_API_KEY"):
        logger.warning("[GNews] Key missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.content.gnews import fetch_gnews_query
        
        logger.info("[Runner] Starting GNews...")
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="GNews",
            object_type="article",
            fetcher_func=fetch_gnews_query,
            quota_service=GNewsQuotaService(),
            enrichment_service=EnrichmentService(),
            discovery_service=DiscoveryService(),
            cooldown_service=CooldownService(),
            source_filter="gnews",
            limit=limit,
            cooldown_hours=24
        )
        logger.info(f"[Runner] GNews success — {count} stored")
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
        if isinstance(e, PipelineFatalError):
            logger.critical("[Runner] GNews fetch ABORTED: %s", str(e))
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            logger.warning("[Runner] GNews quota exceeded: %s", str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        logger.exception("[Runner] GNews fetch failed")
        return {"status": "error", "error": str(e)}

def run_rss_fetch(limit: int | None = None):
    """Fetch from configured RSS feeds."""
    try:
        from app.integrations.content.rss import fetch_rss_query, RSS_FEEDS
        
        # Flatten RSS feeds
        flat_queries = []
        for section, categories in RSS_FEEDS.items():
            for category, feeds in categories.items():
                for f in feeds:
                    flat_queries.append({
                        "query": f, "section": section, "category": category,
                        "topics": [], "brands": [],
                        "intent": "News" if section == "news" else "Review"
                    })

        logger.info("[Runner] Starting RSS feeds...")
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="RSS",
            object_type="article",
            fetcher_func=fetch_rss_query,
            quota_service=GenericQuotaService(),
            enrichment_service=EnrichmentService(),
            discovery_service=None, # Passed via manual_queries
            cooldown_service=CooldownService(),
            source_filter="rss",
            limit=limit,
            cooldown_hours=4,
            manual_queries=flat_queries
        )
        logger.info(f"[Runner] RSS success — {count} stored")
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        logger.exception("[Runner] RSS fetch failed")
        return {"status": "error", "error": str(e)}

def run_sitemap_gen():
    """Generates the static sitemap file."""
    try:
        from app.application.system.sitemap import generate_static_sitemap
        from flask import current_app
        count = generate_static_sitemap(current_app)
        logger.info("[Runner] Sitemap generated with %d URLs", count)
    except Exception:
        logger.exception("[Runner] Sitemap generation failed")
