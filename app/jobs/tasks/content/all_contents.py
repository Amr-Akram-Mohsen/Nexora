import logging
from .articles import run_newsapi_fetch, run_gnews_fetch, run_rss_fetch
from .videos import run_youtube_fetch
from .posts import run_reddit_fetch

logger = logging.getLogger(__name__)


def run_content_fetch(limit: int | None = None):
    """Fetch all active content sources and return a summary report."""
    mode = f"TEST MODE — capping at {limit} queries/source" if limit else "PRODUCTION MODE"
    logger.info("[Runner] ====== NEXORA GLOBAL DISCOVERY ENGINE STARTED ======")
    logger.info("[Runner] %s", mode)

    results = {
        "newsapi": run_newsapi_fetch(limit=limit),
        "gnews":   run_gnews_fetch(limit=limit),
        "youtube": run_youtube_fetch(limit=limit),
        "rss":     run_rss_fetch(limit=limit),
        "reddit":  run_reddit_fetch(limit=limit),
    }

    logger.info("[Runner] ====== DISCOVERY COMPLETE — SUMMARY REPORT ======")
    for source, res in results.items():
        status = res.get("status", "error").upper()
        count  = res.get("count", 0)
        reason = res.get("reason", "")
        if reason:
            logger.info("[Runner]  %-10s  %s (%s)", source, status, reason)
        else:
            logger.info("[Runner]  %-10s  %s  (%d new contents)", source, status, count)

    logger.info("[Runner] Full summary: %s", results)
    return results
