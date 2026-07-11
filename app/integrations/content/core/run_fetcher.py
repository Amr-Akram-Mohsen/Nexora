import logging

from flask import current_app

from app.core.extensions import db
from app.application.content.workflows.ingestion import run_orchestrated_ingestion
from .api_fetchers import (
    fetch_newsapi_query,
    fetch_newsapi_ai_query,
    fetch_gnews_query,
    fetch_youtube_query,
    fetch_reddit_query,
)
from .rss import fetch_rss_query

from app.shared.utils.logging import (
    log_integration_warning,
    log_integration_error,
)

from ..exceptions import (
    PipelineFatalError,
    PipelineQuotaExceededError,
)

logger = logging.getLogger(__name__)


FETCHER_FUNCS_MAP = {
    "newsapi": fetch_newsapi_query,
    "newsapi_ai": fetch_newsapi_ai_query,
    "gnews": fetch_gnews_query,
    "rss": fetch_rss_query,
    "youtube": fetch_youtube_query,
    "reddit": fetch_reddit_query,
}


def run_fetcher(
    *,
    source_name: str,
    object_type: str,
    api_key_name: str | None = None,
):
    if api_key_name and not current_app.config.get(api_key_name):
        log_integration_warning(
            logger,
            source_name,
            reason="key_missing",
        )

        return {
            "status": "skipped",
            "reason": "key_missing",
        }

    try:
        import time
        from sqlalchemy.exc import OperationalError

        last_error = None
        for attempt in range(3):
            try:
                count = run_orchestrated_ingestion(
                    session=db.session,
                    source_name=source_name,
                    object_type=object_type,
                    api_fetcher=FETCHER_FUNCS_MAP.get(source_name),
                )

                return {
                    "status": "success",
                    "count": count,
                }
            except OperationalError as e:
                last_error = e
                db.session.rollback()
                if attempt < 2:
                    logger.warning(
                        "[DB] transient connection error (attempt %d/3) - retrying in 30s... err=%s",
                        attempt + 1,
                        e,
                    )
                    time.sleep(30)
                else:
                    raise

    except Exception as e:
        db.session.rollback()

        if isinstance(e, PipelineFatalError):
            log_integration_error(
                logger,
                source_name,
                e,
                status="aborted",
            )

            return {
                "status": "fatal_error",
                "error": str(e),
            }

        if isinstance(e, PipelineQuotaExceededError):
            log_integration_warning(
                logger,
                source_name,
                reason="quota_exceeded",
                error=str(e),
            )

            return {
                "status": "quota_exceeded",
                "error": str(e),
            }

        log_integration_error(
            logger,
            source_name,
            e,
        )

        return {
            "status": "error",
            "error": str(e),
        }
