# app/jobs/tasks/content/articles.py
"""
Orchestrates all article scraper/discovery jobs.
Balanced discovery across Electronics, Perfumes, and Accessories.
Fails gracefully if API keys are missing.
"""
import logging
from flask import current_app
from app.application.content.ingestion_workflow import run_orchestrated_ingestion
from app.core.extensions import db

from app.shared.utils.logging import log_integration_warning, log_integration_error

logger = logging.getLogger(__name__)

def run_newsapi_fetch():
    """
    Fetch from NewsAPI (tech/fragrance/fashion).

    Uses the fetch limit defined in the source profile.
    The taxonomy-group cursor in the workflow rotates groups across executions so
    coverage spreads without exhausting the daily API quota at once.
    """
    if not current_app.config.get("NEWS_API_KEY"):
        log_integration_warning(logger, "newsapi", reason="key_missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="newsapi",
            object_type="article",
        )
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
        if isinstance(e, PipelineFatalError):
            log_integration_error(logger, "newsapi", e, status="aborted")
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            log_integration_warning(logger, "newsapi", reason="quota_exceeded", error=str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        log_integration_error(logger, "newsapi", e)
        return {"status": "error", "error": str(e)}


def run_gnews_fetch():
    """
    Fetch from GNews (regional/global).

    Uses the fetch limit defined in the source profile.
    """
    if not current_app.config.get("GNEWS_API_KEY"):
        log_integration_warning(logger, "gnews", reason="key_missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="gnews",
            object_type="article",
        )
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
        if isinstance(e, PipelineFatalError):
            log_integration_error(logger, "gnews", e, status="aborted")
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            log_integration_warning(logger, "gnews", reason="quota_exceeded", error=str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        log_integration_error(logger, "gnews", e)
        return {"status": "error", "error": str(e)}


def run_rss_fetch():
    """
    Fetch from configured RSS feeds.

    Processes feeds in incremental batches using the source profile limits.
    Progress is logged after each feed so monitoring is continuous.
    """
    try:
        from app.integrations.content.rss import RSS_FEEDS

        flat_queries = []
        for section, categories in RSS_FEEDS.items():
            for category, feeds in categories.items():
                for f in feeds:
                    flat_queries.append({
                        "query": f, "section": section, "category": category,
                        "topics": [], "brands": [],
                        "intent": "News" if section == "news" else "Review",
                    })

        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="rss",
            object_type="article",
            manual_queries=flat_queries,
        )
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        log_integration_error(logger, "rss", e)
        return {"status": "error", "error": str(e)}


def run_sitemap_gen():
    """Generates the static sitemap file."""
    try:
        from app.application.system.sitemap import generate_static_sitemap
        from flask import current_app
        count = generate_static_sitemap(current_app)
        logger.info("[Runner] Sitemap generated  urls=%d", count)
    except Exception as e:
        log_integration_error(logger, "sitemap", e)
