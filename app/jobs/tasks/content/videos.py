import logging
from flask import current_app
from app.core.extensions import db
from app.application.content.ingestion_workflow import run_orchestrated_ingestion
from app.shared.utils.logging import log_integration_warning, log_integration_error

logger = logging.getLogger(__name__)


def run_youtube_fetch():
    """
    Fetch video reviews from YouTube.

    Uses the fetch limit and quota costs defined in the source profile.
    The taxonomy-group cursor in the workflow rotates through
    electronics -> perfumes -> accessories across successive runs.
    """
    if not current_app.config.get("YOUTUBE_API_KEY"):
        log_integration_warning(logger, "youtube", reason="key_missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.social.youtube import fetch_youtube_query

        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="youtube",
            object_type="video",
        )
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
        if isinstance(e, PipelineFatalError):
            log_integration_error(logger, "youtube", e, status="aborted")
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            log_integration_warning(logger, "youtube", reason="quota_exceeded", error=str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        log_integration_error(logger, "youtube", e)
        return {"status": "error", "error": str(e)}
