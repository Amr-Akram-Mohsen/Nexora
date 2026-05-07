import logging
from .articles import run_newsapi_fetch, run_gnews_fetch, run_rss_fetch
from .videos import run_youtube_fetch
from .posts import run_reddit_fetch
from app.shared.constants.core import FetchLimits

logger = logging.getLogger(__name__)


def run_content_fetch(limit: int | None = None):
    """
    Fetch all active content sources and return a summary report.

    When ``limit`` is supplied it overrides FetchLimits for every source,
    useful for test/debug runs (e.g. limit=2 to smoke-test all sources
    with minimal API usage).

    When ``limit`` is None each source uses its own FetchLimits default,
    which keeps quota usage controlled while maximising coverage.
    """
    if limit is not None:
        mode = f"OVERRIDE MODE — capping all sources at {limit} queries"
    else:
        mode = (
            f"PRODUCTION MODE — "
            f"newsapi={FetchLimits.NEWSAPI}  gnews={FetchLimits.GNEWS}  "
            f"youtube={FetchLimits.YOUTUBE}  rss={FetchLimits.RSS}  "
            f"reddit={FetchLimits.REDDIT}"
        )

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
            logger.info("[Runner]  %-10s  %s  stored=%d", source, status, count)

    logger.info("[Runner] Full summary: %s", results)
    return results
