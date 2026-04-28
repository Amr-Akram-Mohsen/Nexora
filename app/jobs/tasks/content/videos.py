import logging
from flask import current_app

logger = logging.getLogger(__name__)

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

