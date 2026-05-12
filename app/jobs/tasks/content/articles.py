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


logger = logging.getLogger(__name__)

def run_newsapi_fetch():
    """
    Fetch from NewsAPI (tech/fragrance/fashion).

    Uses the fetch limit defined in the source profile.
    The taxonomy-group cursor in the workflow rotates groups across executions so
    coverage spreads without exhausting the daily API quota at once.
    """
    if not current_app.config.get("NEWS_API_KEY"):
        logger.warning("[FETCH][newsapi] skipped  reason=key_missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:

        # logger.info("[FETCH][newsapi] run started  limit=%s", limit)
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
            logger.critical("[FETCH][newsapi] aborted  error=%s", str(e))
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            logger.warning("[FETCH][newsapi] quota_exceeded  error=%s", str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        logger.exception("[FETCH][newsapi] unexpected error")
        return {"status": "error", "error": str(e)}


def run_gnews_fetch():
    """
    Fetch from GNews (regional/global).

    Uses the fetch limit defined in the source profile.
    """
    if not current_app.config.get("GNEWS_API_KEY"):
        logger.warning("[FETCH][gnews] skipped  reason=key_missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        # logger.info("[FETCH][gnews] run started  limit=%s", limit)
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
            logger.critical("[FETCH][gnews] aborted  error=%s", str(e))
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            logger.warning("[FETCH][gnews] quota_exceeded  error=%s", str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        logger.exception("[FETCH][gnews] unexpected error")
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

        logger.info(
            "[FETCH][rss] run started  feeds_total=%d  limit=%s",
            # len(flat_queries), limit,
        )
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="rss",
            object_type="article",
            manual_queries=flat_queries,
        )
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        logger.exception("[FETCH][rss] unexpected error")
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
