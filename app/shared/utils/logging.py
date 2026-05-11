# app/shared/utils/logging.py
"""
Minimal structured logging helpers for Nexora.
Keeps log lines consistent and readable across integrations and routes.

Format examples:
  [INTEGRATION][newsapi] start  query="AI"
  [INTEGRATION][newsapi] success  items=15
  [INTEGRATION][newsapi] error  type=HTTPError message="403 Forbidden"

  [ROUTE][/content] start  query="tech"
  [ROUTE][/content] success  items=10 template="index.html"
"""
import logging
from typing import Any


def log_integration_start(logger: logging.Logger, name: str, **params: Any) -> None:
    """Log the start of an integration call with its input parameters."""
    param_str = "  " + "  ".join(f'{k}="{v}"' for k, v in params.items()) if params else ""
    logger.info("[INTEGRATION][%s] start%s", name, param_str)


def log_integration_success(logger: logging.Logger, name: str, items: int, **extra: Any) -> None:
    """Log a successful integration result."""
    extra_str = "  " + "  ".join(f"{k}={v}" for k, v in extra.items()) if extra else ""
    logger.info("[INTEGRATION][%s] success  items=%d%s", name, items, extra_str)


def log_integration_error(
    logger: logging.Logger,
    name: str,
    error: Exception,
    *,
    exc_info: bool = False,
    **extra: Any,
) -> None:
    """Log an integration failure with error type and message."""
    extra_str = "  " + "  ".join(f"{k}={v}" for k, v in extra.items()) if extra else ""
    logger.warning(
        "[INTEGRATION][%s] error  type=%s  message=%s%s",
        name,
        type(error).__name__,
        str(error),
        extra_str,
        exc_info=exc_info,
    )


def log_integration_warning(logger: logging.Logger, name: str, reason: str, **extra: Any) -> None:
    """Log a soft-fail / no-content warning for an integration call."""
    extra_str = "  " + "  ".join(f"{k}={v}" for k, v in extra.items()) if extra else ""
    logger.warning("[INTEGRATION][%s] warning  reason=%s%s", name, reason, extra_str)


# ── Scraping-specific helpers ─────────────────────────────────────────────────

def log_scrape_start(logger: logging.Logger, url: str) -> None:
    """Log that a scrape attempt is beginning for a URL."""
    logger.info("[SCRAPE] start  url=%s", url)


def log_scrape_success(logger: logging.Logger, url: str, words: int, source: str) -> None:
    """Log a successful scrape result."""
    logger.info("[SCRAPE] success  source=%s  words=%d  url=%s", source, words, url)


def log_scrape_error(logger: logging.Logger, url: str, reason: str) -> None:
    """Log a scrape failure with a short reason string."""
    logger.warning("[SCRAPE] error  reason=%s  url=%s", reason, url)


def log_route_start(logger: logging.Logger, route: str, **params: Any) -> None:
    """Log the start of a route handler."""
    param_str = "  " + "  ".join(f'{k}="{v}"' for k, v in params.items()) if params else ""
    logger.info("[ROUTE][%s] start%s", route, param_str)


def log_route_success(
    logger: logging.Logger,
    route: str,
    *,
    items: int | None = None,
    template: str | None = None,
    status: int = 200,
) -> None:
    """Log a successful route response."""
    parts = [f"status={status}"]
    if items is not None:
        parts.append(f"items={items}")
    if template:
        parts.append(f'template="{template}"')
    logger.info("[ROUTE][%s] success  %s", route, "  ".join(parts))


def log_route_error(logger: logging.Logger, route: str, error: Exception, *, exc_info: bool = True) -> None:
    """Log a route-level error."""
    logger.error(
        "[ROUTE][%s] error  type=%s  message=%s",
        route,
        type(error).__name__,
        str(error),
        exc_info=exc_info,
    )


# ── Fetch-progress helpers ────────────────────────────────────────────────────

def log_fetch_progress(
    logger: logging.Logger,
    source: str,
    *,
    query: str,
    completed: int,
    total: int,
    stored: int,
    group: str = "",
) -> None:
    """
    Emit a single-line progress update after each query completes.

    Example output::

        [FETCH][newsapi] progress  query="AI news"  completed=3/7  stored=5  group=electronics
    """
    group_str = f"  group={group}" if group else ""
    logger.info(
        "[FETCH][%s] progress  query=\"%s\"  completed=%d/%d  stored=%d%s",
        source, query, completed, total, stored, group_str,
    )


def log_fetch_query_start(logger: logging.Logger, source: str, *, query: str, group: str = "") -> None:
    """Log the beginning of a single query within a batch run."""
    group_str = f"  group={group}" if group else ""
    logger.info("[FETCH][%s] start  query=\"%s\"%s", source, query, group_str)


def log_fetch_query_error(
    logger: logging.Logger,
    source: str,
    *,
    query: str,
    error: Exception,
    group: str = "",
) -> None:
    """Log a per-query failure without stopping the run."""
    group_str = f"  group={group}" if group else ""
    logger.warning(
        "[FETCH][%s] error  query=\"%s\"  type=%s  message=%s%s",
        source, query, type(error).__name__, str(error), group_str,
    )


def log_item_ingested(logger: logging.Logger, source: str, title: str, status: str = "stored", **extra: Any) -> None:
    """Log details about a specific item being ingested."""
    extra_str = "  " + "  ".join(f'{k}={v}' for k, v in extra.items()) if extra else ""
    # We use INFO for new items, and DEBUG for updates to keep logs clean
    lvl = logging.INFO if status == "stored" else logging.DEBUG
    logger.log(lvl, "[INGEST][%s] %-8s  title=\"%s\"%s", source, status, title[:60], extra_str)


def log_item_skipped(logger: logging.Logger, source: str, title: str, reason: str, **extra: Any) -> None:
    """Log why an item was skipped during ingestion."""
    extra_str = "  " + "  ".join(f'{k}={v}' for k, v in extra.items()) if extra else ""
    logger.debug("[INGEST][%s] skipped   reason=%-15s  title=\"%s\"%s", source, reason, title[:60], extra_str)


def log_query_summary(
    logger: logging.Logger,
    source: str,
    *,
    query: str,
    stored: int,
    updated: int,
    skipped: int,
    group: str = ""
) -> None:
    """Emit a final summary of ingestion results for a single query."""
    group_str = f"  group={group}" if group else ""
    logger.info(
        "[INGEST][%s] query_done  stored=%d  updated=%d  skipped=%d  query=\"%s\"%s",
        source, stored, updated, skipped, query, group_str
    )
