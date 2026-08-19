"""
Content fetcher execution runners.

Provides single-source runners (YouTube, NewsAPI AI) and the global
content discovery orchestrator (run_content_fetch).
"""
from __future__ import annotations

import logging
from app.integrations.content.core.run_fetcher import run_fetcher
from app.shared.utils.logging import log_runner_banner

logger = logging.getLogger(__name__)


def run_youtube_fetch():
    """Execute YouTube video discovery fetch."""
    return run_fetcher(
        source_name="youtube",
        object_type="video",
        api_key_name="YOUTUBE_API_KEY",
    )


def run_newsapi_ai_fetch():
    """Execute NewsAPI AI article discovery fetch."""
    return run_fetcher(
        source_name="newsapi_ai",
        object_type="article",
        api_key_name="NEWSAPI_AI_API_KEY",
    )


_SOURCES = [
    ("newsapi_ai", run_newsapi_ai_fetch),
    ("youtube", run_youtube_fetch),
]


def run_content_fetch() -> dict:
    """
    Fetch all active content sources and return a summary report.

    Each source is wrapped in its own try/except so a fatal crash in one
    source does not prevent subsequent sources from running.
    """
    log_runner_banner(
        logger,
        "NEXORA GLOBAL DISCOVERY ENGINE STARTED",
    )

    results: dict = {}
    for source_name, runner in _SOURCES:
        try:
            results[source_name] = runner()
        except Exception as exc:
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
