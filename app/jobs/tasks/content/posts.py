import logging
from flask import current_app

logger = logging.getLogger(__name__)

def run_reddit_fetch(limit: int | None = None):
    """Fetch community posts from Reddit."""
    if not current_app.config.get("REDDIT_CLIENT_ID"):
        logger.warning("[Reddit] Keys missing")
        return {"status": "skipped", "reason": "keys_missing"}

    try:
        from app.integrations.social.reddit import fetch_all_reddit
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError

        logger.info("[Runner] Starting Reddit...")
        count = fetch_all_reddit(limit=limit)
        logger.info(f"[Runner] Reddit success — {count} stored")
        return {"status": "success", "count": count}

    except PipelineFatalError as e:
        logger.critical("[Runner] Reddit fetch ABORTED due to fatal error: %s", str(e))
        return {"status": "fatal_error", "error": str(e)}
    except PipelineQuotaExceededError as e:
        logger.warning("[Runner] Reddit quota exceeded: %s", str(e))
        return {"status": "quota_exceeded", "error": str(e)}
    except Exception as e:
        logger.exception("[Runner] Reddit fetch failed with unexpected error")
        return {"status": "error", "error": str(e)}
