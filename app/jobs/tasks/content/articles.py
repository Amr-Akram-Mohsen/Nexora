# app/jobs/tasks/content/articles.py
"""
Orchestrates all article scraper/discovery jobs.
Balanced discovery across Electronics, Perfumes, and Accessories.
Fails gracefully if API keys are missing.
"""
import logging
from flask import current_app

logger = logging.getLogger(__name__)

from app.application.content.ingestion_workflow import run_orchestrated_ingestion
from app.application.content.ingestion.services import (
    DiscoveryService, EnrichmentService, NewsApiQuotaService,
    GNewsQuotaService, GenericQuotaService, CooldownService,
    ClassificationService
)
from app.core.extensions import db


def run_newsapi_fetch(limit: int | None = None, should_scrape: bool = False):
    """
    Fetch from NewsAPI (tech/fragrance/fashion).

    Args:
        limit:        Cap the number of queries processed per run.
        should_scrape: When True, triggers full article scraping after ingestion.
                       Default False — stores metadata only.
    """
    if not current_app.config.get("NEWS_API_KEY"):
        logger.warning("[NewsAPI] Key missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.content.newsapi import fetch_newsapi_query

        logger.info("[Runner] Starting NewsAPI  should_scrape=%s", should_scrape)
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="NewsAPI",
            object_type="article",
            fetcher_func=fetch_newsapi_query,
            quota_service=NewsApiQuotaService(),
            enrichment_service=EnrichmentService(should_scrape=should_scrape),
            discovery_service=DiscoveryService(),
            cooldown_service=CooldownService(),
            classification_service=ClassificationService(),
            source_filter="newsapi",
            limit=limit,
            cooldown_hours=6,
        )
        logger.info("[Runner] NewsAPI done  stored=%d", count)
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
        if isinstance(e, PipelineFatalError):
            logger.critical("[Runner] NewsAPI ABORTED: %s", str(e))
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            logger.warning("[Runner] NewsAPI quota exceeded: %s", str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        logger.exception("[Runner] NewsAPI fetch failed")
        return {"status": "error", "error": str(e)}


def run_gnews_fetch(limit: int | None = None, should_scrape: bool = False):
    """
    Fetch from GNews (regional/global).

    Args:
        limit:        Cap the number of queries processed per run.
        should_scrape: When True, triggers full article scraping after ingestion.
                       Default False — stores metadata only.
    """
    if not current_app.config.get("GNEWS_API_KEY"):
        logger.warning("[GNews] Key missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.content.gnews import fetch_gnews_query

        logger.info("[Runner] Starting GNews  should_scrape=%s", should_scrape)
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="GNews",
            object_type="article",
            fetcher_func=fetch_gnews_query,
            quota_service=GNewsQuotaService(),
            enrichment_service=EnrichmentService(should_scrape=should_scrape),
            discovery_service=DiscoveryService(),
            cooldown_service=CooldownService(),
            classification_service=ClassificationService(),
            source_filter="gnews",
            limit=limit,
            cooldown_hours=24,
        )
        logger.info("[Runner] GNews done  stored=%d", count)
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
        if isinstance(e, PipelineFatalError):
            logger.critical("[Runner] GNews ABORTED: %s", str(e))
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            logger.warning("[Runner] GNews quota exceeded: %s", str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        logger.exception("[Runner] GNews fetch failed")
        return {"status": "error", "error": str(e)}


def run_rss_fetch(limit: int | None = None, should_scrape: bool = False):
    """
    Fetch from configured RSS feeds.

    Args:
        limit:        Cap the number of feeds processed per run.
        should_scrape: When True, triggers full article scraping after ingestion.
                       Default False — stores metadata only.
    """
    try:
        from app.integrations.content.rss import fetch_rss_query, RSS_FEEDS

        flat_queries = []
        for section, categories in RSS_FEEDS.items():
            for category, feeds in categories.items():
                for f in feeds:
                    flat_queries.append({
                        "query": f, "section": section, "category": category,
                        "topics": [], "brands": [],
                        "intent": "News" if section == "news" else "Review",
                    })

        logger.info("[Runner] Starting RSS feeds  should_scrape=%s", should_scrape)
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="RSS",
            object_type="article",
            fetcher_func=fetch_rss_query,
            quota_service=GenericQuotaService(),
            enrichment_service=EnrichmentService(should_scrape=should_scrape),
            discovery_service=None,
            cooldown_service=CooldownService(),
            classification_service=ClassificationService(),
            source_filter="rss",
            limit=limit,
            cooldown_hours=4,
            manual_queries=flat_queries,
        )
        logger.info("[Runner] RSS done  stored=%d", count)
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
        logger.info("[Runner] Sitemap generated  urls=%d", count)
    except Exception:
        logger.exception("[Runner] Sitemap generation failed")
