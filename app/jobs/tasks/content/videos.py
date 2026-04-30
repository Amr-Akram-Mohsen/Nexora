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
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError

        logger.info("[Runner] Starting YouTube reviews...")
        count = fetch_youtube_reviews(limit=limit)
        logger.info(f"[Runner] YouTube success — {count} stored")
        return {"status": "success", "count": count}

    except PipelineFatalError as e:
        logger.critical("[Runner] YouTube fetch ABORTED due to fatal error: %s", str(e))
        return {"status": "fatal_error", "error": str(e)}
    except PipelineQuotaExceededError as e:
        logger.warning("[Runner] YouTube quota exceeded: %s", str(e))
        return {"status": "quota_exceeded", "error": str(e)}
    except Exception as e:
        logger.exception("[Runner] YouTube fetch failed with unexpected error")
        return {"status": "error", "error": str(e)}

