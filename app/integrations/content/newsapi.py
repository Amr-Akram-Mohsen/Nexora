# app/integrations/content/newsapi.py
import logging
import requests
from flask import current_app
from app.integrations.exceptions import PipelineQuotaExceededError

logger = logging.getLogger(__name__)

def fetch_newsapi_query(q_obj: dict) -> list[dict]:
    """
    Pure fetcher for NewsAPI.
    Focuses only on API request and returning raw data.
    """
    api_key = current_app.config.get("NEWS_API_KEY")
    if not api_key:
        logger.warning("[NewsAPI] No API key")
        print("[NewsAPI] No API key")
        return []

    q_text = q_obj["query"]
    
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q":        q_text,
                "language": "en",
                "sortBy":   "publishedAt",
                "pageSize": 80,
                "apiKey":   api_key,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("articles", [])
        
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 403:
            raise PipelineQuotaExceededError("NewsAPI Quota Exceeded")
        logger.warning("[NewsAPI] API request failed for query '%s': %s", q_text, str(e))
        return []

def fetch_all_sections(limit: int | None = None) -> int:
    """Entry point refactored to use IngestionWorkflow."""
    from app.application.content.ingestion_workflow import run_orchestrated_ingestion
    from app.integrations.external.api import can_call_newsapi, record_newsapi_call
    
    return run_orchestrated_ingestion(
        source_name="NewsAPI",
        object_type="article",
        fetcher_func=fetch_newsapi_query,
        can_call_func=can_call_newsapi,
        record_call_func=record_newsapi_call,
        source_filter="newsapi",
        limit=limit,
        cooldown_hours=6
    )
