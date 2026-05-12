import logging
from flask import current_app

from app.core.extensions import db

from app.application.content.ingestion_workflow import run_orchestrated_ingestion
from app.application.content.ingestion.services import (
    DiscoveryService, EnrichmentService, GenericQuotaService, CooldownService,
    ClassificationService
)
from app.shared.constants.source_profiles import SOURCE_PROFILES

logger = logging.getLogger(__name__)


def run_reddit_fetch(limit: int | None = SOURCE_PROFILES['reddit'].fetch_limit):
    """
    Fetch community posts from Reddit.

    Processes a controlled batch per run (default: FetchLimits.REDDIT queries).
    The taxonomy-group cursor rotates groups across successive runs.

    Args:
        limit: Max queries per run.  Pass ``None`` for unlimited.
    """
    if not current_app.config.get("REDDIT_CLIENT_ID"):
        logger.warning("[FETCH][reddit] skipped  reason=keys_missing")
        return {"status": "skipped", "reason": "keys_missing"}

    try:
        from app.integrations.social.reddit import fetch_reddit_query

        logger.info("[FETCH][reddit] run started  limit=%s", limit)
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="reddit",
            object_type="post",
            fetcher_func=fetch_reddit_query,
            # quota_service=GenericQuotaService(),
            # enrichment_service=EnrichmentService(),
            # discovery_service=DiscoveryService(),
            # cooldown_service=CooldownService(),
            # classification_service=ClassificationService(),
            # source_filter="reddit",
            # limit=limit,
            # cooldown_hours=SOURCE_PROFILES['reddit'].cooldown_hours,
        )
        logger.info("[FETCH][reddit] run done  total_stored=%d", count)
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
        if isinstance(e, PipelineFatalError):
            logger.critical("[FETCH][reddit] aborted  error=%s", str(e))
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            logger.warning("[FETCH][reddit] quota_exceeded  error=%s", str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        logger.exception("[FETCH][reddit] unexpected error")
        return {"status": "error", "error": str(e)}
