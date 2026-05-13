import logging
from typing import Optional, List, Dict, Any

# ---------------------------------------------------------------------------
# Integration Lifecycle
# ---------------------------------------------------------------------------

def log_integration_start(logger: logging.Logger, name: str, **kwargs) -> None:
    """Log the start of an integration fetch."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug("[INTEGRATION][%s] start  %s", name, extras)

def log_integration_success(logger: logging.Logger, name: str, items: int, **kwargs) -> None:
    """Log a successful integration fetch."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug("[INTEGRATION][%s] success  items=%d  %s", name, items, extras)

def log_integration_error(logger: logging.Logger, name: str, error: Exception, **kwargs) -> None:
    """Log an integration error."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.error("[INTEGRATION][%s] error  %s  err=%s", name, extras, error, stacklevel=2)

def log_integration_warning(logger: logging.Logger, name: str, reason: str, **kwargs) -> None:
    """Log an integration skip or minor issue."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.warning("[INTEGRATION][%s] skipped  reason=%s  %s", name, reason, extras, stacklevel=2)


# ---------------------------------------------------------------------------
# Scraping & Extraction
# ---------------------------------------------------------------------------

def log_scrape_start(logger: logging.Logger, url: str) -> None:
    """Log the start of a scraping attempt."""
    logger.debug("[SCRAPE] start  url=%s", url)

def log_scrape_success(logger: logging.Logger, url: str, words: int, source: str) -> None:
    """Log a successful scrape."""
    logger.info("[SCRAPE] success  words=%d  source=%s  url=%s", words, source, url)

def log_scrape_error(logger: logging.Logger, url: str, reason: str) -> None:
    """Log a failed scrape."""
    logger.warning("[SCRAPE] failed  reason=%s  url=%s", reason, url, stacklevel=2)


# ---------------------------------------------------------------------------
# Ingestion Workflow
# ---------------------------------------------------------------------------

def log_item_ingested(logger: logging.Logger, source: str, title: str, status: str, published: bool = None, **kwargs) -> None:
    """Log an item being stored or updated in the DB."""
    pub_str = f"  published={published}" if published is not None else ""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info("[INGEST][%s] %-8s  title=\"%s\"%s  %s", source, status, title, pub_str, extras)

def log_item_skipped(logger: logging.Logger, source: str, title: str, reason: str, **kwargs) -> None:
    """Log an item being skipped during ingestion."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug("[INGEST][%s] skipped  reason=%-20s  title=\"%s\"  %s", source, reason, title, extras)


# ---------------------------------------------------------------------------
# Routing & API
# ---------------------------------------------------------------------------

def log_route_call(logger: logging.Logger, route: str, method: str, **kwargs) -> None:
    """Log an incoming API or UI route call."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info("[ROUTE] %-6s  %-20s  %s", method, route, extras)



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
        stacklevel=2
    )


# ---------------------------------------------------------------------------
# Batch & Fetch Runner (High-level orchestration)
# ---------------------------------------------------------------------------

def log_fetch_progress(
    logger: logging.Logger,
    source: str,
    query: str,
    completed: int,
    total: int,
    stored: int,
    extra: str = "",
) -> None:
    """Log a single query line in a multi-query fetch run."""
    logger.info(
        "[FETCH][%s] progress  query=\"%s\"  completed=%d/%d  stored=%d%s",
        source,
        query[:40],
        completed,
        total,
        stored,
        f"  {extra}" if extra else "",
    )

def log_fetch_query_error(
    logger: logging.Logger,
    source: str,
    query: str,
    error: Exception,
    group: str = "",
) -> None:
    """Log an error for a single query in a run."""
    logger.error(
        "[FETCH][%s] error  query=\"%s\"  group=%s  err=%s",
        source,
        query,
        group,
        error,
        stacklevel=2
    )

def log_fetch_run_start(
    logger: logging.Logger,
    source: str,
    *,
    group: str,
    tasks: int,
    eligible: int,
    limit: Any,
) -> None:
    """Log the start of a full fetch run."""
    logger.info(
        "[FETCH][%s] run_start  group=%s  tasks=%d  eligible=%d  limit=%s",
        source,
        group,
        tasks,
        eligible,
        limit,
    )

def log_fetch_run_done(
    logger: logging.Logger,
    source: str,
    *,
    stored: int,
    updated: int,
    elapsed: float,
    next_group: str,
) -> None:
    """Log the completion of a full fetch run."""
    logger.info(
        "[FETCH][%s] run_done  stored=%d  updated=%d  elapsed=%.1fs  next=%s",
        source,
        stored,
        updated,
        elapsed,
        next_group,
    )

def log_batch_rotation(
    logger: logging.Logger,
    source: str,
    *,
    next_group: str,
) -> None:
    """Log taxonomy cursor rotation."""
    logger.info(
        "[BATCH][%s] cursor_advanced  next_group=%s",
        source,
        next_group,
    )


def log_quota_exhausted(logger: logging.Logger, source: str) -> None:
    """Log that an API quota has been exhausted, halting the run."""
    logger.warning("[FETCH][%s] quota_exhausted — halting run", source, stacklevel=2)


def log_runner_banner(logger: logging.Logger, message: str) -> None:
    """Log a high-level banner for the task runner."""
    logger.info("[Runner] ====== %s ======", message.upper())


def log_cooldown_skip(logger: logging.Logger, reason: str, **kwargs) -> None:
    """Log a fetch skip due to cooldown."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info("[COOLDOWN] skip  reason=%s  %s", reason, extras)
