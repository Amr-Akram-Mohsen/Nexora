import logging
from .articles import run_newsapi_fetch, run_gnews_fetch, run_rss_fetch
from .videos import run_youtube_fetch
from .posts import run_reddit_fetch
from app.shared.utils.logging import log_runner_banner

logger = logging.getLogger(__name__)


def run_content_fetch():
    """
    Fetch all active content sources and return a summary report.

    This coordinator orchestrates discovery across all configured sources
    (RSS, NewsAPI, GNews, YouTube, Reddit). Each source uses its own 
    dedicated profile for fetch limits and cooldowns.
    """

    log_runner_banner(logger, "NEXORA GLOBAL DISCOVERY ENGINE STARTED")

    results = {
        "newsapi": run_newsapi_fetch(),
        "gnews":   run_gnews_fetch(),
        "youtube": run_youtube_fetch(),
        "rss":     run_rss_fetch(),
        "reddit":  run_reddit_fetch(),
    }

    log_runner_banner(logger, "DISCOVERY COMPLETE — SUMMARY REPORT")
    for source, res in results.items():
        status = res.get("status", "error").upper()
        count  = res.get("count", 0)
        reason = res.get("reason", "")
        if reason:
            logger.info("[Runner]  %-10s  %s (%s)", source, status, reason)
        else:
            logger.info("[Runner]  %-10s  %s  stored=%d", source, status, count)

    logger.info("[Runner] Full summary: %s", results)
    return results
