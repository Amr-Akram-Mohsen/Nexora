# app/jobs/tasks/content/fetch_articles.py
"""
Orchestrates all scraper/discovery jobs.
Balanced discovery across Electronics, Perfumes, and Accessories.
Fails gracefully if API keys are missing.
"""
import logging
from flask import current_app

logger = logging.getLogger(__name__)

def run_newsapi_fetch(limit: int | None = None):
    """Fetch from NewsAPI (tech/fragrance/fashion)."""
    if not current_app.config.get("NEWS_API_KEY"):
        logger.warning("[NewsAPI] Key missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.content.newsapi import fetch_all_sections as fetch_newsapi
        logger.info("[Runner] Starting NewsAPI...")
        count = fetch_newsapi(limit=limit)
        logger.info(f"[Runner] NewsAPI success — {count} stored")
        return {"status": "success", "count": count}
    except Exception as e:
        logger.exception("[Runner] NewsAPI fetch failed")
        return {"status": "error", "error": str(e)}

def run_gnews_fetch(limit: int | None = None):
    """Fetch from GNews (regional/global)."""
    if not current_app.config.get("GNEWS_API_KEY"):
        logger.warning("[GNews] Key missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.content.gnews import fetch_all_gnews
        logger.info("[Runner] Starting GNews...")
        count = fetch_all_gnews(limit=limit)
        logger.info(f"[Runner] GNews success — {count} stored")
        return {"status": "success", "count": count}
    except Exception as e:
        logger.exception("[Runner] GNews fetch failed")
        return {"status": "error", "error": str(e)}

def run_youtube_fetch(limit: int | None = None):
    """Fetch video reviews from YouTube."""
    if not current_app.config.get("YOUTUBE_API_KEY"):
        logger.warning("[YouTube] Key missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.social.youtube import fetch_youtube_reviews
        logger.info("[Runner] Starting YouTube reviews...")
        count = fetch_youtube_reviews(limit=limit)
        logger.info(f"[Runner] YouTube success — {count} stored")
        return {"status": "success", "count": count}
    except Exception as e:
        logger.exception("[Runner] YouTube fetch failed")
        return {"status": "error", "error": str(e)}

def run_rss_fetch(limit: int | None = None):
    """Fetch from configured RSS feeds."""
    try:
        from app.integrations.content.rss import fetch_all_rss
        logger.info("[Runner] Starting RSS feeds...")
        count = fetch_all_rss(limit=limit)
        logger.info(f"[Runner] RSS success — {count} stored")
        return {"status": "success", "count": count}
    except Exception as e:
        logger.exception("[Runner] RSS fetch failed")
        return {"status": "error", "error": str(e)}

def run_reddit_fetch(limit: int | None = None):
    """Fetch community posts from Reddit."""
    if not current_app.config.get("REDDIT_CLIENT_ID"):
        logger.warning("[Reddit] Keys missing")
        return {"status": "skipped", "reason": "keys_missing"}

    try:
        from app.integrations.social.reddit import fetch_all_reddit
        logger.info("[Runner] Starting Reddit...")
        count = fetch_all_reddit(limit=limit)
        logger.info(f"[Runner] Reddit success — {count} stored")
        return {"status": "success", "count": count}
    except Exception as e:
        logger.exception("[Runner] Reddit fetch failed")
        return {"status": "error", "error": str(e)}


def run_article_fetch(limit: int | None = None):
    """Fetch all active article sources and return a summary report."""
    print("\n" + "="*50)
    print("🚀 NEXORA GLOBAL DISCOVERY ENGINE STARTED")
    if limit:
        print(f"⚠️  TEST MODE ENABLED: Capping at {limit} queries per source")
    print("="*50 + "\n")

    results = {
        "newsapi": run_newsapi_fetch(limit=limit),
        "gnews": run_gnews_fetch(limit=limit),
        "youtube": run_youtube_fetch(limit=limit),
        "rss": run_rss_fetch(limit=limit),
        "reddit": run_reddit_fetch(limit=limit)
    }
    
    print("\n" + "="*50)
    print("🏁 DISCOVERY COMPLETE - SUMMARY REPORT")
    print("="*50)
    for source, res in results.items():
        status = res.get("status", "error").upper()
        count = res.get("count", 0)
        print(f" - {source.ljust(10)}: {status} ({count} new articles)")
    print("="*50 + "\n")

    logger.info(f"[Runner] Complete! Summary: {results}")
    return results


def run_sitemap_gen():
    """Generates the static sitemap file."""
    try:
        from app.domains.system.sitemap import generate_static_sitemap
        from flask import current_app
        count = generate_static_sitemap(current_app)
        logger.info("[Runner] Sitemap generated with %d URLs", count)
    except Exception:
        logger.exception("[Runner] Sitemap generation failed")
