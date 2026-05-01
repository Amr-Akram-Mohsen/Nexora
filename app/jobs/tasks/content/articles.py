# app/jobs/tasks/content/articles.py
"""
Orchestrates all scraper/discovery jobs.
Balanced discovery across Electronics, Perfumes, and Accessories.
Fails gracefully if API keys are missing.
"""
import logging
from flask import current_app

logger = logging.getLogger(__name__)

def run_newsapi_fetch(limit: int | None = None):
    """Fetch from NewsAPI (tech/fragrance/fashion)."""
    if not current_app.config.get("NEWS_API_KEY"):
        logger.warning("[NewsAPI] Key missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.content.newsapi import fetch_all_sections as fetch_newsapi
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError

        logger.info("[Runner] Starting NewsAPI...")
        count = fetch_newsapi(limit=limit)
        logger.info(f"[Runner] NewsAPI success — {count} stored")
        return {"status": "success", "count": count}

    except PipelineFatalError as e:
        logger.critical("[Runner] NewsAPI fetch ABORTED due to fatal error: %s", str(e))
        return {"status": "fatal_error", "error": str(e)}
    except PipelineQuotaExceededError as e:
        logger.warning("[Runner] NewsAPI quota exceeded: %s", str(e))
        return {"status": "quota_exceeded", "error": str(e)}
    except Exception as e:
        logger.exception("[Runner] NewsAPI fetch failed with unexpected error")
        return {"status": "error", "error": str(e)}

def run_gnews_fetch(limit: int | None = None):
    """Fetch from GNews (regional/global)."""
    if not current_app.config.get("GNEWS_API_KEY"):
        logger.warning("[GNews] Key missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.content.gnews import fetch_all_gnews
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError

        logger.info("[Runner] Starting GNews...")
        count = fetch_all_gnews(limit=limit)
        logger.info(f"[Runner] GNews success — {count} stored")
        return {"status": "success", "count": count}

    except PipelineFatalError as e:
        logger.critical("[Runner] GNews fetch ABORTED due to fatal error: %s", str(e))
        return {"status": "fatal_error", "error": str(e)}
    except PipelineQuotaExceededError as e:
        logger.warning("[Runner] GNews quota exceeded: %s", str(e))
        return {"status": "quota_exceeded", "error": str(e)}
    except Exception as e:
        logger.exception("[Runner] GNews fetch failed with unexpected error")
        return {"status": "error", "error": str(e)}

def run_rss_fetch(limit: int | None = None):
    """Fetch from configured RSS feeds."""
    try:
        from app.integrations.content.rss import fetch_all_rss
        from app.integrations.exceptions import PipelineFatalError

        logger.info("[Runner] Starting RSS feeds...")
        count = fetch_all_rss(limit=limit)
        logger.info(f"[Runner] RSS success — {count} stored")
        return {"status": "success", "count": count}

    except PipelineFatalError as e:
        logger.critical("[Runner] RSS fetch ABORTED due to fatal error: %s", str(e))
        return {"status": "fatal_error", "error": str(e)}
    except Exception as e:
        logger.exception("[Runner] RSS fetch failed with unexpected error")
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
