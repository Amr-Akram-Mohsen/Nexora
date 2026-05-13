import logging
from flask import current_app
from app.core.extensions import db
from app.application.content.ingestion_workflow import run_orchestrated_ingestion
from app.shared.utils.logging import log_integration_warning, log_integration_error

logger = logging.getLogger(__name__)


def run_reddit_fetch():
    """
    Fetch community posts from Reddit.

    Processes a controlled batch per run (default: FetchLimits.REDDIT queries).
    The taxonomy-group cursor rotates groups across successive runs.

    Args:
        limit: Max queries per run.  Pass ``None`` for unlimited.
    """
    if not current_app.config.get("REDDIT_CLIENT_ID"):
        log_integration_warning(logger, "reddit", reason="keys_missing")
        return {"status": "skipped", "reason": "keys_missing"}

    try:
        from app.integrations.social.reddit import fetch_reddit_query

        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="reddit",
            object_type="post",
        )
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
        if isinstance(e, PipelineFatalError):
            log_integration_error(logger, "reddit", e, status="aborted")
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            log_integration_warning(logger, "reddit", reason="quota_exceeded", error=str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        log_integration_error(logger, "reddit", e)
        return {"status": "error", "error": str(e)}
