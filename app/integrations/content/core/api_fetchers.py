import logging
import time
import re
from flask import current_app
from app.shared.utils.logging import (
    log_integration_start,
    log_integration_success,
    log_integration_error,
    log_integration_warning,
)
from .http import _get_session
from .fetch_engine import safe_get_json, safe_post_json
from .fetchers_mappers import map_newsapi_ai, map_youtube

logger = logging.getLogger(__name__)

def _parse_to_er_query(query_str: str) -> dict:
    blocks = []
    
    def replacer(match):
        blocks.append(match.group(1))
        return f"__BLOCK_{len(blocks)-1}__"
    
    q_stripped = re.sub(r"\(([^)]+)\)", replacer, query_str)
    
    and_conditions = []
    
    for term in q_stripped.split():
        term = term.strip()
        if not term:
            continue
            
        if term.startswith("__BLOCK_"):
            try:
                block_idx = int(term.replace("__BLOCK_", "").replace("__", ""))
                or_terms = blocks[block_idx].split(" OR ")
                or_conditions = [{"keyword": t.strip().strip('"')} for t in or_terms if t.strip()]
                
                if len(or_conditions) == 1:
                    and_conditions.append(or_conditions[0])
                elif len(or_conditions) > 1:
                    and_conditions.append({"$or": or_conditions})
            except Exception as e:
                pass
        else:
            if term not in ["AND", "OR"]:
                and_conditions.append({"keyword": term.strip('"')})
                
    if not and_conditions:
        return {"$and": [{"keyword": query_str}]}
        
    return {"$and": and_conditions}

def fetch_newsapi_ai_query(q_obj, **kwargs):
    # Support both EVENT_REGISTRY_API_KEY and NEWSAPI_AI_API_KEY for backward compatibility
    api_key = current_app.config.get("EVENT_REGISTRY_API_KEY") or current_app.config.get("NEWSAPI_AI_API_KEY")
    if not api_key:
        log_integration_warning(logger, "newsapi_ai", reason="no_api_key")
        return []

    q_text = q_obj.get("query", "")
    category = q_obj.get("category", "")
    section = q_obj.get("section", "")

    log_integration_start(logger, "newsapi_ai", query=q_text, category=category)
    time.sleep(2.5)
    session = _get_session()

    and_conditions = _parse_to_er_query(q_text).get("$and", [])

    # Map Nexora taxonomy to NewsAPI AI (Event Registry) categories
    cat_lower = category.lower()
    
    if "tech" in cat_lower:
        and_conditions.append({"categoryUri": "dmoz/Computers"})
    elif "perfume" in cat_lower or "fragrance" in cat_lower:
        and_conditions.append({"categoryUri": "dmoz/Shopping/Health_and_Beauty/Fragrances"})
    elif "accessori" in cat_lower or "wearable" in cat_lower:
        and_conditions.append({"categoryUri": "dmoz/Shopping/Jewelry"})
        
    and_conditions.append({"lang": "eng"})

    query_obj = {
        "$query": {"$and": and_conditions},
        "$filter": {
            "isDuplicate": "skipDuplicates",
            "dataType": ["news", "pr", "blog"]
        }
    }

    payload = {
        "action": "getArticles",
        "query": query_obj,
        "articlesPage": 1,
        "articlesCount": 20,
        "articlesSortBy": "date",
        "articlesSortByAsc": False,
        "resultType": "articles",
        "apiKey": api_key,
        "includeArticleConcepts": True,
        "includeArticleCategories": True,
    }

    data = safe_post_json(
        session,
        "https://eventregistry.org/api/v1/article/getArticles",
        json_data=payload,
        timeout=(5, 15),
        logger=logger,
        source_name="newsapi_ai",
    )

    products = map_newsapi_ai(data)
    if isinstance(products, list):
        log_integration_success(logger, "newsapi_ai", products=len(products), query=q_text)
    else:
        log_integration_warning(
            logger, "newsapi_ai", reason="unexpected_response_shape", query=q_text
        )

    return products




import re

def parse_youtube_duration(duration_str):
    """Parses ISO 8601 duration (e.g., PT1H2M10S) to seconds."""
    if not duration_str: return 0
    match = re.match(r'^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$', duration_str)
    if not match: return 0
    h, m, s = match.groups()
    return int(h or 0) * 3600 + int(m or 0) * 60 + int(s or 0)

def fetch_youtube_query(q_obj, **kwargs):
    api_key = current_app.config.get("YOUTUBE_API_KEY")
    if not api_key:
        log_integration_warning(logger, "youtube", reason="no_api_key")
        return []

    _ARABIC_CHARS = set("ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي")

    q_text = q_obj.get("query", "")
    fallback_region = "SA" if len(q_text) % 2 == 0 else "AE"
    region_code = q_obj.get("region", fallback_region).upper()
    category = q_obj.get("category", "")
    video_category_id = "28" if "technology" in category.lower() else None

    log_integration_start(logger, "youtube", query=q_text, region=region_code)

    params = {
        "part": "snippet",
        "q": q_text,
        "type": "video",
        "relevanceLanguage": "ar" if any(c in q_text for c in _ARABIC_CHARS) else "en",
        "regionCode": region_code,
        "order": "relevance",
        "maxResults": 10,
        "key": api_key,
    }
    if video_category_id:
        params["videoCategoryId"] = video_category_id

    session = _get_session()

    data = safe_get_json(
        session,
        "https://www.googleapis.com/youtube/v3/search",
        params=params,
        timeout=(10),
        logger=logger,
        source_name="youtube",
    )

    products = map_youtube(data, region=region_code)

    # Fetch duration for videos
    if products and api_key:
        video_ids = [p.external_id for p in products if p.external_id]
        if video_ids:
            videos_params = {
                "part": "contentDetails",
                "id": ",".join(video_ids),
                "key": api_key,
            }
            videos_data = safe_get_json(
                session,
                "https://www.googleapis.com/youtube/v3/videos",
                params=videos_params,
                timeout=(5, 10),
                logger=logger,
                source_name="youtube",
            )
            if videos_data and "items" in videos_data:
                durations = {}
                for item in videos_data["items"]:
                    durations[item["id"]] = parse_youtube_duration(item.get("contentDetails", {}).get("duration"))
                for p in products:
                    if p.external_id in durations:
                        p.duration_seconds = durations[p.external_id]

    if isinstance(products, list):
        log_integration_success(logger, "youtube", products=len(products), query=q_text)
    else:
        log_integration_warning(
            logger, "youtube", reason="unexpected_response_shape", query=q_text
        )

    return products

