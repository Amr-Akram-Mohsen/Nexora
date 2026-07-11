# app/integrations/scheduler.py
"""
Background job scheduler using APScheduler.
Runs inside the Flask process OR as a standalone process via `flask run-scheduler`.

Jobs registered here and their recommended intervals:

  Source     | Interval | Rationale
  -----------|----------|--------------------------------------------------
  newsapi    | 4h       | 100 req/day ÷ 6 runs = 15/run (max_queries_per_run)
  gnews      | 6h       | 100 req/day ÷ 4 runs = 25/run, use 12 (extra margin)
  youtube    | 3h       | 10,000 units/day = 100 searches; 8 runs × 10 = 80 ✓
  reddit     | 4h       | Unlimited quota; 6 runs × 25 = 150 posts/day
  rss        | 2h       | Etag-protected — near-free, gets freshest feeds
  enrich     | 2h       | Publish pending articles that were scraped

All jobs push a Flask app context so SQLAlchemy sessions work safely.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from app.shared.utils.logging import log_integration_error

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_in_context(app, job_fn_path: str):
    """Push a Flask app context and run the requested job function by path."""
    with app.app_context():
        try:
            # Lazy import inside context — avoids circular imports at startup
            module_path, fn_name = job_fn_path.rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            fn = getattr(module, fn_name)
            logger.info("[Scheduler] Starting job: %s", fn_name)
            fn()
            logger.info("[Scheduler] Finished job: %s", fn_name)
        except Exception:
            logger.exception("[Scheduler] Job '%s' failed", job_fn_path)


def init_scheduler(app):
    """
    Initialise and start the APScheduler background scheduler.
    Called once from create_app() or via `flask run-scheduler`.
    Safe to call multiple times (guards against double-start in debug reloader).
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="Asia/Riyadh", daemon=True)

    # ── RSS: every 2 hours ───────────────────────────────────────
    # Etag/Last-Modified protected — almost free. Gets the freshest feeds.
    _scheduler.add_job(
        func=lambda: _run_in_context(
            app, "app.integrations.content.fetcher_runners.all_contents.run_rss_fetch"
        ),
        trigger=IntervalTrigger(hours=2),
        id="fetch_rss",
        replace_existing=True,
    )

    # ── NewsAPI: every 4 hours ───────────────────────────────────
    # 100 req/day budget. 4h × 6 runs = 15 max_queries_per_run each. ✓
    _scheduler.add_job(
        func=lambda: _run_in_context(
            app, "app.integrations.content.fetcher_runners.all_contents.run_newsapi_fetch"
        ),
        trigger=IntervalTrigger(hours=4),
        id="fetch_newsapi",
        replace_existing=True,
    )

    # ── GNews: every 6 hours ─────────────────────────────────────
    # 100 req/day budget. 6h × 4 runs = 12 max_queries_per_run each. ✓
    _scheduler.add_job(
        func=lambda: _run_in_context(
            app, "app.integrations.content.fetcher_runners.all_contents.run_gnews_fetch"
        ),
        trigger=IntervalTrigger(hours=6),
        id="fetch_gnews",
        replace_existing=True,
    )

    # ── YouTube: every 3 hours ───────────────────────────────────
    # 10,000 units/day = 100 searches. 3h × 8 runs × 10 searches = 80. ✓
    _scheduler.add_job(
        func=lambda: _run_in_context(
            app, "app.integrations.content.fetcher_runners.all_contents.run_youtube_fetch"
        ),
        trigger=IntervalTrigger(hours=3),
        id="fetch_youtube",
        replace_existing=True,
    )

    # ── Reddit: every 4 hours ────────────────────────────────────
    # Unlimited OAuth quota. 4h × 6 runs × 25 posts = 150 posts/day.
    _scheduler.add_job(
        func=lambda: _run_in_context(
            app, "app.integrations.content.fetcher_runners.all_contents.run_reddit_fetch"
        ),
        trigger=IntervalTrigger(hours=4),
        id="fetch_reddit",
        replace_existing=True,
    )

    # ── Article enrichment: every 2 hours ────────────────────────
    # Scrapes and publishes pending articles. Light workload.
    def _run_enrich():
        with app.app_context():
            try:
                from app.application.content.workflows.enrichment import enrich_discovered_articles
                count = enrich_discovered_articles(50)
                logger.info("[Scheduler] Enriched %d articles", count)
            except Exception:
                logger.exception("[Scheduler] Enrichment job failed")

    _scheduler.add_job(
        func=_run_enrich,
        trigger=IntervalTrigger(hours=2),
        id="enrich_articles",
        replace_existing=True,
    )

    # ── Amazon price refresh: every 12 hours ─────────────────────
    _scheduler.add_job(
        func=lambda: _run_in_context(
            app, "app.application.content.workflows.enrichment.enrich_discovered_articles"
        ),
        trigger=IntervalTrigger(hours=12),
        id="refresh_prices",
        replace_existing=True,
    )

    # ── Sitemap: once a day ───────────────────────────────────────
    def _run_sitemap():
        with app.app_context():
            try:
                from app.application.system.sitemap import generate_static_sitemap
                count = generate_static_sitemap(app)
                logger.info("[Scheduler] Sitemap generated  urls=%d", count)
            except Exception:
                logger.exception("[Scheduler] Sitemap job failed")

    _scheduler.add_job(
        func=_run_sitemap,
        trigger=IntervalTrigger(hours=24),
        id="generate_sitemap",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "[Scheduler] All jobs registered. "
        "RSS=2h, NewsAPI=4h, GNews=6h, YouTube=3h, Reddit=4h, Enrich=2h"
    )


def get_scheduler() -> BackgroundScheduler | None:
    """Return the global scheduler instance (for manual triggers in dashboard)."""
    return _scheduler
