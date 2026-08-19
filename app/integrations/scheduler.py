# app/integrations/scheduler.py
"""
Background job scheduler using APScheduler.
Runs inside the Flask process OR as a standalone process via `flask run-scheduler`.

Jobs registered here and their recommended intervals:

  Source     | Interval | Rationale
  -----------|----------|--------------------------------------------------
  newsapi_ai | 4h       | 100 req/day
  youtube    | 3h       | 10,000 units/day = 100 searches; 8 runs × 10 = 80 ✓
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

    # ── NewsAPI AI: every 4 hours ───────────────────────────────────
    _scheduler.add_job(
        func=lambda: _run_in_context(
            app, "app.integrations.content.runners.run_newsapi_ai_fetch"
        ),
        trigger=IntervalTrigger(hours=4),
        id="fetch_newsapi_ai",
        replace_existing=True,
    )

    # ── YouTube: every 3 hours ───────────────────────────────────
    # 10,000 units/day = 100 searches. 3h × 8 runs × 10 searches = 80. ✓
    _scheduler.add_job(
        func=lambda: _run_in_context(
            app, "app.integrations.content.runners.run_youtube_fetch"
        ),
        trigger=IntervalTrigger(hours=3),
        id="fetch_youtube",
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
        "NewsAPI_AI=4h, YouTube=3h, Enrich=2h"
    )


def get_scheduler() -> BackgroundScheduler | None:
    """Return the global scheduler instance (for manual triggers in dashboard)."""
    return _scheduler
