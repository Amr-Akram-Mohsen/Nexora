import logging
from flask import current_app

logger = logging.getLogger(__name__)

from app.core.extensions import db
from app.application.content.ingestion_workflow import run_orchestrated_ingestion


def run_youtube_fetch():
    """
    Fetch video reviews from YouTube.

    Uses the fetch limit and quota costs defined in the source profile.
    The taxonomy-group cursor in the workflow rotates through
    electronics -> perfumes -> accessories across successive runs.
    """
    if not current_app.config.get("YOUTUBE_API_KEY"):
        logger.warning("[FETCH][youtube] skipped  reason=key_missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.social.youtube import fetch_youtube_query

        # logger.info("[FETCH][youtube] run started  limit=%s", limit)
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="youtube",
            object_type="video",
        )
        logger.info("[FETCH][youtube] run done  total_stored=%d", count)
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
        if isinstance(e, PipelineFatalError):
            logger.critical("[FETCH][youtube] aborted  error=%s", str(e))
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            logger.warning("[FETCH][youtube] quota_exceeded  error=%s", str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        logger.exception("[FETCH][youtube] unexpected error")
        return {"status": "error", "error": str(e)}
