import logging
from flask import current_app

logger = logging.getLogger(__name__)

from app.core.extensions import db
from app.application.content.ingestion_workflow import run_orchestrated_ingestion
from app.application.content.ingestion.services import (
    DiscoveryService, EnrichmentService, YouTubeQuotaService, CooldownService,
    ClassificationService
)
from app.shared.constants.core import FetchLimits


def run_youtube_fetch(limit: int | None = FetchLimits.YOUTUBE):
    """
    Fetch video reviews from YouTube.

    Each search.list call costs 100 quota units.  The default limit of
    FetchLimits.YOUTUBE queries caps a single run at ~1 000 units
    (10 % of the 10 000-unit daily budget).

    The taxonomy-group cursor in the workflow rotates through
    electronics → perfumes → accessories across successive runs.

    Args:
        limit: Max queries to process this run.  Pass ``None`` for unlimited
               (the YouTubeQuotaService run-budget will still apply).
    """
    if not current_app.config.get("YOUTUBE_API_KEY"):
        logger.warning("[FETCH][youtube] skipped  reason=key_missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.social.youtube import fetch_youtube_query

        logger.info("[FETCH][youtube] run started  limit=%s", limit)
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="youtube",
            object_type="video",
            fetcher_func=fetch_youtube_query,
            quota_service=YouTubeQuotaService(),
            enrichment_service=EnrichmentService(),
            discovery_service=DiscoveryService(),
            cooldown_service=CooldownService(),
            classification_service=ClassificationService(),
            source_filter="youtube",
            limit=limit,
            cooldown_hours=12,
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
