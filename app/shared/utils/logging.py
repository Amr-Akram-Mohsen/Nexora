import logging
from typing import Any

# ---------------------------------------------------------------------------
# Integration Lifecycle
# ---------------------------------------------------------------------------


def log_integration_start(logger: logging.Logger, name: str, **kwargs) -> None:
    """Log the start of an integration fetch."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug("[INTEGRATION][%s] start  %s", name, extras)


def log_integration_success(
    logger: logging.Logger, name: str, products: int, **kwargs
) -> None:
    """Log a successful integration fetch."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug("[INTEGRATION][%s] success  products=%d  %s", name, products, extras)


def log_integration_error(
    logger: logging.Logger, name: str, error: Exception, **kwargs
) -> None:
    """Log an integration error."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.error(
        "[INTEGRATION][%s] error  %s  err=%s", name, extras, error, stacklevel=2
    )


def log_integration_warning(
    logger: logging.Logger, name: str, reason: str, **kwargs
) -> None:
    """Log an integration skip or minor issue."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.warning(
        "[INTEGRATION][%s] skipped  reason=%s  %s", name, reason, extras, stacklevel=2
    )


# ---------------------------------------------------------------------------
# Scraping & Extraction
# ---------------------------------------------------------------------------


def log_scrape_start(logger: logging.Logger, url: str) -> None:
    """Log the start of a scraping attempt."""
    logger.debug("[SCRAPE] start  url=%s", url)


def log_scrape_success(
    logger: logging.Logger, url: str, words: int, source: str
) -> None:
    """Log a successful scrape."""
    logger.info("[SCRAPE] success  words=%d  source=%s  url=%s", words, source, url)


def log_scrape_error(logger: logging.Logger, url: str, reason: str) -> None:
    """Log a failed scrape."""
    logger.warning("[SCRAPE] failed  reason=%s  url=%s", reason, url, stacklevel=2)


# ---------------------------------------------------------------------------
# Ingestion Workflow
# ---------------------------------------------------------------------------


def log_item_ingested(
    logger: logging.Logger,
    source: str,
    content_id: int | str,
    object_id: int | str,
    status: str,
    published: bool = None,
    **kwargs,
) -> None:
    """Log an product being stored or updated in the DB."""
    pub_str = f"  published={published}" if published is not None else ""
    
    # Format updated_relationships nicer if present
    if "updated_relationships" in kwargs:
        ur = kwargs.pop("updated_relationships")
        if isinstance(ur, dict): 
            summary = []
            for k, v in ur.items():
                if isinstance(v, list) or isinstance(v, dict):
                    summary.append(f"{k}={len(v)}")
                else:
                    summary.append(f"{k}={v}")
            kwargs["updates"] = "[" + ", ".join(summary) + "]"
        else:
            kwargs["updates"] = str(ur)[:100] + "..." if len(str(ur)) > 100 else str(ur)

    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(
        '[INGEST][%s] %-8s  content_id=%s  object_id=%s%s  %s', source, status, content_id, object_id, pub_str, extras
    )


def log_item_skipped(
    logger: logging.Logger, source: str, title: str, reason: str, **kwargs
) -> None:
    """Log an product being skipped during ingestion."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug(
        '[INGEST][%s] skipped  reason=%-20s  title="%s"  %s',
        source,
        reason,
        title,
        extras,
    )


# ---------------------------------------------------------------------------
# Routing & API
# ---------------------------------------------------------------------------


def log_route_call(logger: logging.Logger, route: str, method: str, **kwargs) -> None:
    """Log an incoming API or UI route call."""
    extras = "  ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info("[ROUTE] %-6s  %-20s  %s", method, route, extras)


def log_route_start(logger: logging.Logger, route: str, **params: Any) -> None:
    """Log the start of a route handler."""
    param_str = (
        "  " + "  ".join(f'{k}="{v}"' for k, v in params.items()) if params else ""
    )
    logger.info("[ROUTE][%s] start%s", route, param_str)


def log_route_success(
    logger: logging.Logger,
    route: str,
    *,
    products: int | None = None,
    template: str | None = None,
    status: int = 200,
) -> None:
    """Log a successful route response."""
    parts = [f"status={status}"]
    if products is not None:
        parts.append(f"products={products}")
    if template:
        parts.append(f'template="{template}"')
    logger.info("[ROUTE][%s] success  %s", route, "  ".join(parts))


def log_route_error(
    logger: logging.Logger, route: str, error: Exception, *, exc_info: bool = True
) -> None:
    """Log a route-level error."""
    logger.error(
        "[ROUTE][%s] error  type=%s  message=%s",
        route,
        type(error).__name__,
        str(error),
        exc_info=exc_info,
        stacklevel=2,
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
        '[FETCH][%s] progress  query="%s"  completed=%d/%d  stored=%d%s',
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
        '[FETCH][%s] error  query="%s"  group=%s  err=%s',
        source,
        query,
        group,
        error,
        stacklevel=2,
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


def log_velocity_cooldown(
    logger: logging.Logger,
    source: str,
    *,
    category: str,
    velocity: str,
    base_hours: float,
    effective_hours: float,
) -> None:
    """Log when velocity scaling changes the effective cooldown for a category.

    Only emitted at DEBUG level to avoid noise; useful when diagnosing why
    a category is fetched more or less often than the base profile suggests.
    """
    logger.debug(
        "[COOLDOWN][%s] velocity_scaled  category=%s  velocity=%s  base=%.1fh  effective=%.1fh",
        source,
        category,
        velocity,
        base_hours,
        effective_hours,
    )


# ---------------------------------------------------------------------------
# Commercial Product Pipeline Logging
# ---------------------------------------------------------------------------


def log_commercial_discovery_start(logger: logging.Logger, source_type: str, category: str, page: int) -> None:
    """Log the start of commercial product discovery."""
    logger.info("[COMMERCIAL][DISCOVERY] start  source=%s  category=\"%s\"  page=%d", source_type, category, page)


def log_commercial_discovery_success(logger: logging.Logger, source_type: str, category: str, count: int, page: int) -> None:
    """Log successful commercial product discovery."""
    logger.info("[COMMERCIAL][DISCOVERY] success  source=%s  category=\"%s\"  discovered=%d  page=%d", source_type, category, count, page)


def log_commercial_enqueue(logger: logging.Logger, enqueued: int, duplicates: int) -> None:
    """Log discovery queue batch summary."""
    logger.info("[COMMERCIAL][QUEUE] enqueued=%d  duplicates=%d", enqueued, duplicates)


def log_commercial_scrape_start(logger: logging.Logger, url: str) -> None:
    """Log start of product page scraping in commercial pipeline."""
    logger.info("[COMMERCIAL][SCRAPE] start  url=%s", url)


def log_commercial_scrape_success(logger: logging.Logger, url: str, name: str, variants_count: int, images_count: int) -> None:
    """Log successful product page scrape in commercial pipeline."""
    logger.info("[COMMERCIAL][SCRAPE] success  variants=%d  images=%d  title=\"%s\"  url=%s", variants_count, images_count, (name or "")[:50], url)


def log_commercial_scrape_failed(logger: logging.Logger, url: str, reason: str) -> None:
    """Log failed product page scrape in commercial pipeline."""
    logger.warning("[COMMERCIAL][SCRAPE] failed  reason=%s  url=%s", reason, url)


def log_commercial_ingest_success(logger: logging.Logger, product_id: int, name: str, store_slug: str, price: Any, currency: str) -> None:
    """Log successful insertion of product into database."""
    logger.info("[COMMERCIAL][INGEST] inserted  product_id=%s  store=%s  price=%s %s  title=\"%s\"", product_id, store_slug, price, currency or "", (name or "")[:50])


def log_commercial_pipeline_done(logger: logging.Logger, stats: dict) -> None:
    """Log overall commercial pipeline completion stats."""
    logger.info("[COMMERCIAL][PIPELINE] done  discovered=%d  enqueued=%d  duplicates=%d  scraped=%d  inserted=%d  failed=%d  skipped=%d",
                stats.get("discovered", 0), stats.get("enqueued", 0), stats.get("duplicates", 0),
                stats.get("scraped", 0), stats.get("inserted", 0), stats.get("failed", 0), stats.get("skipped", 0))


# ---------------------------------------------------------------------------
# Commercial Browser Lifecycle Logging
# ---------------------------------------------------------------------------


def log_commercial_browser_launch(logger: logging.Logger, profile_dir: str, channel: str) -> None:
    """Log successful browser launch with profile and channel details."""
    logger.info("[COMMERCIAL][BROWSER] launch  channel=%s  profile=%s", channel, profile_dir)


def log_commercial_browser_profile_locked(logger: logging.Logger, profile_dir: str) -> None:
    """Log when the Chrome profile directory is locked by a running Chrome process."""
    logger.error(
        "[COMMERCIAL][BROWSER] profile_locked  profile=%s  "
        "action=RAISE  hint=\"Close Google Chrome completely before running the scraper.\"",
        profile_dir,
    )


def log_commercial_browser_fallback(logger: logging.Logger, fallback_dir: str) -> None:
    """Log when the scraper falls back to a secondary (non-default) Chrome profile directory."""
    logger.warning(
        "[COMMERCIAL][BROWSER] fallback  fallback_dir=%s  "
        "note=\"Fallback profile has no Google account session or AliExpress cookies.\"",
        fallback_dir,
    )


def log_commercial_page_navigate(logger: logging.Logger, url: str, wait_strategy: str) -> None:
    """Log page navigation attempt with its wait strategy."""
    logger.info("[COMMERCIAL][PAGE] navigate  strategy=%s  url=%s", wait_strategy, url)


def log_commercial_page_ready(logger: logging.Logger, selector: str, elapsed_ms: float) -> None:
    """Log when a key page element is confirmed present in DOM."""
    logger.info("[COMMERCIAL][PAGE] ready  selector=%s  elapsed_ms=%.0f", selector, elapsed_ms)


def log_commercial_captcha(logger: logging.Logger, url: str) -> None:
    """Log captcha wall detection during scraping."""
    logger.warning("[COMMERCIAL][SCRAPE] captcha_detected  url=%s", url)


def log_commercial_retry(logger: logging.Logger, url: str, attempt: int, max_attempts: int, reason: str) -> None:
    """Log a scrape retry event with attempt counter and reason."""
    logger.warning(
        "[COMMERCIAL][SCRAPE] retry  attempt=%d/%d  reason=%s  url=%s",
        attempt, max_attempts, reason, url,
    )

