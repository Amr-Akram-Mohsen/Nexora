import logging
from flask import current_app

logger = logging.getLogger(__name__)

from app.core.extensions import db
from app.application.content.ingestion_workflow import run_orchestrated_ingestion
from app.application.content.ingestion.services import (
    DiscoveryService, EnrichmentService, YouTubeQuotaService, CooldownService,
    ClassificationService
)

def run_youtube_fetch(limit: int | None = None):
    """Fetch video reviews from YouTube."""
    if not current_app.config.get("YOUTUBE_API_KEY"):
        logger.warning("[YouTube] Key missing")
        return {"status": "skipped", "reason": "key_missing"}

    try:
        from app.integrations.social.youtube import fetch_youtube_query
        
        logger.info("[Runner] Starting YouTube reviews...")
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="YouTube",
            object_type="video",
            fetcher_func=fetch_youtube_query,
            quota_service=YouTubeQuotaService(),
            enrichment_service=EnrichmentService(),
            discovery_service=DiscoveryService(),
            cooldown_service=CooldownService(),
            classification_service=ClassificationService(),
            source_filter="youtube",
            limit=limit,
            cooldown_hours=12
        )
        logger.info(f"[Runner] YouTube success — {count} stored")
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
        if isinstance(e, PipelineFatalError):
            logger.critical("[Runner] YouTube fetch ABORTED: %s", str(e))
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            logger.warning("[Runner] YouTube quota exceeded: %s", str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        logger.exception("[Runner] YouTube fetch failed")
        return {"status": "error", "error": str(e)}

