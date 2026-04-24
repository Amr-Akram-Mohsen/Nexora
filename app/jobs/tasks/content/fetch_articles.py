# app/jobs/tasks/content/fetch_articles.py
"""
Orchestrates all scraper/discovery jobs.
Balanced discovery across Electronics, Perfumes, and Accessories.
Fails gracefully if API keys are missing.
"""
import logging
from flask import current_app

logger = logging.getLogger(__name__)


def run_article_fetch():
    """Fetch all free sources + YouTube with a diverse set of tech/fragrance/fashion queries."""
    # ── NewsAPI (Requires Key) ───────────────────────────────────
    if current_app.config.get("NEWS_API_KEY"):
        try:
            from app.integrations.content.newsapi import fetch_all_sections as fetch_newsapi
            logger.info("[Runner] NewsAPI...")
            fetch_newsapi()
        except Exception:
            logger.exception("[Runner] NewsAPI fetch failed")
    else:
        logger.info("[Runner] Skipping NewsAPI: Key missing")

    # ── GNews (Requires Key) ──────────────────────────────────────
    if current_app.config.get("GNEWS_API_KEY"):
        try:
            from app.integrations.content.gnews import fetch_all_gnews
            logger.info("[Runner] GNews...")
            fetch_all_gnews()
        except Exception:
            logger.exception("[Runner] GNews fetch failed")
    else:
        logger.info("[Runner] Skipping GNews: Key missing")

    # ── YouTube (Requires Key) ───────────────────────────────────
    if current_app.config.get("YOUTUBE_API_KEY"):
        try:
            from app.integrations.social.youtube import fetch_youtube_reviews
            logger.info("[Runner] YouTube reviews...")
            fetch_youtube_reviews()
        except Exception:
            logger.exception("[Runner] YouTube fetch failed")
    else:
        logger.info("[Runner] Skipping YouTube: Key missing")

    # ── RSS (Always Runs) ──────────────────────────────────────────
    try:
        from app.integrations.content.rss import fetch_all_rss
        logger.info("[Runner] RSS feeds...")
        count = fetch_all_rss()
        logger.info("[Runner] RSS done — %d articles stored", count)
    except Exception:
        logger.exception("[Runner] RSS fetch failed")

def run_reddit_fetch():
    """Fetch community posts from diverse subreddits."""
    if not current_app.config.get("REDDIT_CLIENT_ID"):
        logger.info("[Runner] Skipping Reddit: API Keys missing")
        return

    try:
        from app.integrations.social.reddit import fetch_all_reddit
        logger.info("[Runner] Reddit communities...")
        count = fetch_all_reddit()
        logger.info("[Runner] Reddit done — %d posts stored", count)
    except Exception:
        logger.exception("[Runner] Reddit fetch failed")


def run_sitemap_gen():
    """Generates the static sitemap file."""
    try:
        from app.domains.system.sitemap import generate_static_sitemap
        from flask import current_app
        count = generate_static_sitemap(current_app)
        logger.info("[Runner] Sitemap generated with %d URLs", count)
    except Exception:
        logger.exception("[Runner] Sitemap generation failed")

