# app/integrations/social/youtube.py
import logging
import requests
from flask import current_app
from app.integrations.exceptions import PipelineQuotaExceededError
from app.shared.utils.logging import log_integration_start, log_integration_success, log_integration_error

logger = logging.getLogger(__name__)

_NAME = "youtube"
_ARABIC_CHARS = set("ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي")


def fetch_youtube_query(q_obj: dict, **kwargs) -> list[dict]:
    """
    Pure fetcher for YouTube.
    Always returns a list (never None).
    """
    api_key = current_app.config.get("YOUTUBE_API_KEY")
    if not api_key:
        logger.warning("[INTEGRATION][%s] skipped  reason=no_api_key", _NAME)
        return []

    query = q_obj.get("query", "")
    region_code = q_obj.get("region", "SA")
    category = q_obj.get("category", "")
    video_category_id = "28" if "electronics" in category.lower() else None

    log_integration_start(logger, _NAME, query=query, region=region_code)

    params = {
        "part":              "snippet",
        "q":                 query,
        "type":              "video",
        "relevanceLanguage": "ar" if any(c in query for c in _ARABIC_CHARS) else "en",
        "regionCode":        region_code,
        "order":             "relevance",
        "maxResults":        5,
        "key":               api_key,
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

        items_data = resp.json().get("items", [])
        if not isinstance(items_data, list):
            logger.warning("[INTEGRATION][%s] unexpected response shape for query=%s", _NAME, query)
            items_data = []

        raw_items = []
        from app.shared.dto.ingestion import RawItemDTO
        for item in items_data:
            if not isinstance(item, dict):
                continue
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue
            snippet = item.get("snippet", {})
            raw_items.append(RawItemDTO(
                title=snippet.get("title", ""),
                description=snippet.get("description", ""),
                url=f"https://www.youtube.com/watch?v={video_id}",
                thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url"),
                published_at=snippet.get("publishedAt"),
                channel_name=snippet.get("channelTitle", ""),
                is_video=True,
                region=region_code,
                external_id=video_id,
                platform="youtube",
            ))

        log_integration_success(logger, _NAME, items=len(raw_items), query=query, region=region_code)
        return raw_items

    except requests.exceptions.RequestException as e:
        if hasattr(e, "response") and e.response is not None and e.response.status_code == 403:
            raise PipelineQuotaExceededError("YouTube Quota Exceeded")
        log_integration_error(logger, _NAME, e, query=query)
        return []
    except Exception as e:
        log_integration_error(logger, _NAME, e, query=query, exc_info=True)
        return []
