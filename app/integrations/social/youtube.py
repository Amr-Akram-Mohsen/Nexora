# app/integrations/social/youtube.py
import logging
import requests
from flask import current_app
from app.integrations.exceptions import PipelineQuotaExceededError

logger = logging.getLogger(__name__)

def fetch_youtube_query(q_obj: dict) -> list[dict]:
    """
    Pure fetcher for YouTube.
    """
    api_key = current_app.config.get("YOUTUBE_API_KEY")
    if not api_key:
        logger.warning("[YouTube] No API key")
        print("[YouTube] No API key")
        return []

    query = q_obj["query"]
    region_code = q_obj.get("region", "SA")
    
    # Simple mapping for tech category
    video_category_id = "28" if "electronics" in q_obj.get("category", "").lower() else None

    params = {
        "part":             "snippet",
        "q":                query,
        "type":             "video",
        "relevanceLanguage":"ar" if any(c in query for c in 'ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي') else "en",
        "regionCode":       region_code,
        "order":            "relevance",
        "maxResults":       5,
        "key":              api_key,
    }
    if video_category_id:
        params["videoCategoryId"] = video_category_id

    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        
        raw_items = []
        for item in resp.json().get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if not video_id: continue
            snippet = item.get("snippet", {})
            raw_items.append({
                "title":        snippet.get("title", ""),
                "description":  snippet.get("description", ""),
                "url":          f"https://www.youtube.com/watch?v={video_id}",
                "image_url":    snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "published_at": snippet.get("publishedAt"),
                "source_name":  snippet.get("channelTitle", ""),
                "is_video":     True,
                "region":       region_code,
                "external_id":  video_id,
                "platform":     "youtube"
            })
        return raw_items
        
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 403:
            raise PipelineQuotaExceededError("YouTube Quota Exceeded")
        logger.warning("[YouTube] API request failed for query '%s': %s", query, str(e))
        return []

def fetch_youtube_reviews(limit: int | None = None) -> int:
    """Entry point refactored to use IngestionWorkflow."""
    from app.application.content.ingestion_workflow import run_orchestrated_ingestion
    from app.integrations.external.api import can_call_youtube, record_youtube_call
    
    return run_orchestrated_ingestion(
        source_name="YouTube",
        object_type="video",
        fetcher_func=fetch_youtube_query,
        can_call_func=lambda: can_call_youtube(units=100),
        record_call_func=lambda: record_youtube_call(units=100),
        source_filter="youtube",
        limit=limit,
        cooldown_hours=12
    )
