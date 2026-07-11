import logging

from app.integrations.content.fetcher_runners.api_fetchers import (
    run_newsapi_fetch,
    run_event_registry_fetch,
    run_gnews_fetch,
    run_youtube_fetch,
    run_reddit_fetch,
)
# Note: run_newsapi_ai_fetch is not implemented but cli expects it. We provide a dummy if needed or export it if it exists in api_fetchers.
def run_newsapi_ai_fetch():
    pass

from .rss import run_rss_fetch

from app.shared.utils.logging import log_runner_banner

logger = logging.getLogger(__name__)

# Sources in priority order — changing this order changes which source
# gets first access to quota/DB writes when run synchronously.
_SOURCES = [
    ("event_registry", run_event_registry_fetch),
    ("youtube",  run_youtube_fetch),
    ("rss",      run_rss_fetch),
    ("reddit",   run_reddit_fetch),
]


def run_content_fetch():
    """
    Fetch all active content sources and return a summary report.

    Each source is wrapped in its own try/except so a fatal crash in one
    source (e.g. a transient DB issue at source N) does not prevent
    subsequent sources from running.
    """

    log_runner_banner(
        logger,
        "NEXORA GLOBAL DISCOVERY ENGINE STARTED",
    )

    results: dict = {}
    for source_name, runner in _SOURCES:
        try:
            results[source_name] = runner()
        except Exception as exc:  # unexpected — runner should never raise
            logger.error(
                "[Runner] %-10s UNEXPECTED_ERROR  err=%s",
                source_name,
                exc,
                exc_info=True,
            )
            results[source_name] = {"status": "error", "error": str(exc), "count": 0}

    log_runner_banner(
        logger,
        "DISCOVERY COMPLETE — SUMMARY REPORT",
    )

    for source, res in results.items():
        status = res.get("status", "error").upper()
        count = res.get("count", 0)
        reason = res.get("reason", "")

        if reason:
            logger.info(
                "[Runner] %-10s %s (%s)",
                source,
                status,
                reason,
            )
        else:
            logger.info(
                "[Runner] %-10s %s stored=%d",
                source,
                status,
                count,
            )

    logger.info(
        "[Runner] Full summary: %s",
        results,
    )

    return results
