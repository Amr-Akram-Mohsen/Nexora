# app/jobs/scheduler.py
"""
Background job scheduler using APScheduler.
Runs inside the Flask process — no separate server needed.

Jobs registered here:
  - articles  : Fetch new articles from RSS, NewsAPI, GNews, YouTube  (every 6h)
  - reddit    : Fetch community posts from Reddit                      (every 12h)
  - prices    : Refresh Amazon item prices                             (every 12h)
  - amazon    : Discover new products from Amazon PA-API               (every 24h)

All jobs push an app context so they can use SQLAlchemy safely.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_in_context(app, job_type: str):
    """Push a Flask app context and run the requested job."""
    with app.app_context():
        try:
            from app.scrapers.runner import (
                run_article_fetch,
                run_reddit_fetch,
                run_price_refresh,
                run_amazon_discovery,
                run_sitemap_gen,
            )
            jobs = {
                "articles": run_article_fetch,
                "reddit":   run_reddit_fetch,
                "prices":   run_price_refresh,
                "amazon":   run_amazon_discovery,
                "sitemap":  run_sitemap_gen,
            }
            fn = jobs.get(job_type)
            if fn:
                logger.info("[Scheduler] Starting job: %s", job_type)
                fn()
                logger.info("[Scheduler] Finished job: %s", job_type)
            else:
                logger.warning("[Scheduler] Unknown job type: %s", job_type)
        except Exception:
            logger.exception("[Scheduler] Job '%s' failed", job_type)


def init_scheduler(app):
    """
    Initialise and start the scheduler.
    Called once from create_app(). Safe to call multiple times
    (guards against double-start in debug reloader).
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="Asia/Riyadh", daemon=True)

    # ── Article sources: every 6 hours ───────────────────────────
    _scheduler.add_job(
        func=lambda: _run_in_context(app, "articles"),
        trigger=IntervalTrigger(hours=6),
        id="fetch_articles",
        replace_existing=True,
    )

    # ── Reddit community posts: every 12 hours ───────────────────
    _scheduler.add_job(
        func=lambda: _run_in_context(app, "reddit"),
        trigger=IntervalTrigger(hours=12),
        id="fetch_reddit",
        replace_existing=True,
    )

    # ── Amazon price refresh: every 12 hours ─────────────────────
    _scheduler.add_job(
        func=lambda: _run_in_context(app, "prices"),
        trigger=IntervalTrigger(hours=12),
        id="refresh_prices",
        replace_existing=True,
    )

    # ── Amazon product discovery: once a day ─────────────────────
    _scheduler.add_job(
        func=lambda: _run_in_context(app, "amazon"),
        trigger=IntervalTrigger(hours=24),
        id="discover_amazon",
        replace_existing=True,
    )

    # ── Sitemap generation: once a day ───────────────────────────
    _scheduler.add_job(
        func=lambda: _run_in_context(app, "sitemap"),
        trigger=IntervalTrigger(hours=24),
        id="generate_sitemap",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("[Scheduler] All jobs registered and running.")


def get_scheduler() -> BackgroundScheduler | None:
    """Return the global scheduler instance (for manual triggers in dashboard)."""
    return _scheduler
