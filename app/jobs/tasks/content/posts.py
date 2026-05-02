import logging
from flask import current_app

from app.core.extensions import db

from app.application.content.ingestion_workflow import run_orchestrated_ingestion
from app.application.content.ingestion.services import (
    DiscoveryService, EnrichmentService, GenericQuotaService, CooldownService
)

logger = logging.getLogger(__name__)


def run_reddit_fetch(limit: int | None = None):
    """Fetch community posts from Reddit."""
    if not current_app.config.get("REDDIT_CLIENT_ID"):
        logger.warning("[Reddit] Keys missing")
        return {"status": "skipped", "reason": "keys_missing"}

    try:
        from app.integrations.social.reddit import fetch_reddit_query
        
        logger.info("[Runner] Starting Reddit...")
        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="Reddit",
            object_type="post",
            fetcher_func=fetch_reddit_query,
            quota_service=GenericQuotaService(),
            enrichment_service=EnrichmentService(),
            discovery_service=DiscoveryService(),
            cooldown_service=CooldownService(),
            source_filter="reddit",
            limit=limit,
            cooldown_hours=24
        )
        logger.info(f"[Runner] Reddit success — {count} stored")
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
        if isinstance(e, PipelineFatalError):
            logger.critical("[Runner] Reddit fetch ABORTED: %s", str(e))
            return {"status": "fatal_error", "error": str(e)}
        if isinstance(e, PipelineQuotaExceededError):
            logger.warning("[Runner] Reddit quota exceeded: %s", str(e))
            return {"status": "quota_exceeded", "error": str(e)}
        logger.exception("[Runner] Reddit fetch failed")
        return {"status": "error", "error": str(e)}
