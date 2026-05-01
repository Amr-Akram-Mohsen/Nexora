# app/integrations/content/gnews.py
import logging
import requests
from flask import current_app
from app.integrations.exceptions import PipelineQuotaExceededError

logger = logging.getLogger(__name__)

def fetch_gnews_query(q_obj: dict) -> list[dict]:
    """
    Pure fetcher for GNews.
    """
    api_key = current_app.config.get("GNEWS_API_KEY")
    if not api_key:
        logger.warning("[GNews] No API key")
        print("[GNews] No API key")
        return []

    q_text = q_obj["query"]
    country = q_obj.get("region", "sa").lower()
    
    try:
        resp = requests.get(
            "https://gnews.io/api/v4/search",
            params={
                "q":       q_text,
                "lang":    "en" if not any(c in q_text for c in 'ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي') else "ar",
                "country": country,
                "max":     50,
                "apikey":  api_key,
            },
            timeout=10,
        )
        resp.raise_for_status()
        
        articles = resp.json().get("articles", [])
        for a in articles:
            a["image_url"] = a.get("image")
            a["region"] = country.upper()
        return articles
        
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 403:
            raise PipelineQuotaExceededError("GNews Quota Exceeded")
        logger.warning("[GNews] API request failed for query '%s': %s", q_text, str(e))
        return []

def fetch_all_gnews(limit: int | None = None) -> int:
    """Entry point refactored to use IngestionWorkflow."""
    from app.application.content.ingestion_workflow import run_orchestrated_ingestion
    from app.integrations.external.api import can_call_gnews, record_gnews_call
    
    # We need to handle country-specific queries
    # The IngestionWorkflow expects a list of queries. 
    # DiscoveryManager provides these, but GNews logic previously duplicated them for SA/AE.
    # I'll update the discovery logic to include region if needed, 
    # but for now, let's keep it simple.
    
    return run_orchestrated_ingestion(
        source_name="GNews",
        object_type="article",
        fetcher_func=fetch_gnews_query,
        can_call_func=can_call_gnews,
        record_call_func=record_gnews_call,
        source_filter="gnews",
        limit=limit,
        cooldown_hours=8
    )
