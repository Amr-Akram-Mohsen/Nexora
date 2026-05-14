import logging
from app.application.content.workflows.ingestion import run_orchestrated_ingestion
from app.core.extensions import db

from app.shared.utils.logging import log_integration_error

logger = logging.getLogger(__name__)


def run_rss_fetch():
    """
    Fetch from configured RSS feeds.

    Processes feeds in incremental batches using the source profile limits.
    Progress is logged after each feed so monitoring is continuous.
    """
    try:
        from ..core.rss import RSS_FEEDS, fetch_rss_query

        flat_queries = []
        for section, categories in RSS_FEEDS.items():
            for category, feeds in categories.items():
                for f in feeds:
                    flat_queries.append(
                        {
                            "query": f,
                            "section": section,
                            "category": category,
                            "topics": [],
                            "brands": [],
                            "intent": "News" if section == "news" else "Review",
                        }
                    )

        count = run_orchestrated_ingestion(
            session=db.session,
            source_name="rss",
            object_type="article",
            api_fetcher=fetch_rss_query,
            manual_queries=flat_queries,
        )
        return {"status": "success", "count": count}
    except Exception as e:
        db.session.rollback()
        log_integration_error(logger, "rss", e)
        return {"status": "error", "error": str(e)}
