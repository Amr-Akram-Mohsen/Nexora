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
from .fetchers_mappers import map_newsapi, map_newsapi_ai, map_gnews, map_youtube, map_reddit

logger = logging.getLogger(__name__)


def fetch_newsapi_query(q_obj, **kwargs):
    api_key = current_app.config.get("NEWS_API_KEY")
    if not api_key:
        log_integration_warning(logger, "newsapi", reason="no_api_key")
        return []

    q_text = q_obj.get("query", "")

    log_integration_start(logger, "newsapi", query=q_text)
    # 429 Mitigation: NewsAPI has a strict per-second rate limit on free tier.
    # Increasing to 2.5s to be safer against burst detections.
    time.sleep(2.5)
    session = _get_session()

    params = {
        "q": q_text,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20,
        "apiKey": api_key,
    }
    if q_obj.get("from"):
        params["from"] = q_obj["from"]
    if q_obj.get("to"):
        params["to"] = q_obj["to"]

    data = safe_get_json(
        session,
        "https://newsapi.org/v2/everything",
        params=params,
        timeout=(5, 15),
        logger=logger,
        source_name="newsapi",
    )

    items = map_newsapi(data)
    if isinstance(items, list):
        log_integration_success(logger, "newsapi", items=len(items), query=q_text)
    else:
        log_integration_warning(
            logger, "newsapi", reason="unexpected_response_shape", query=q_text
        )

    return items


def fetch_gnews_query(q_obj, **kwargs):
    api_key = current_app.config.get("GNEWS_API_KEY")
    if not api_key:
        log_integration_warning(logger, "gnews", reason="no_api_key")
        return []

    q_text = q_obj.get("query", "")
    region = q_obj.get("region", "en").lower()

    log_integration_start(logger, "gnews", query=q_text)
    time.sleep(2.5)
    session = _get_session()

    params = {
        "q": q_text,
        "lang": "en",
        "country": region if len(region) == 2 else "us",
        "max": 10,
        "apikey": api_key,
    }

    data = safe_get_json(
        session,
        "https://gnews.io/api/v4/search",
        params=params,
        timeout=(5, 15),
        logger=logger,
        source_name="gnews",
    )

    items = map_gnews(data, region=region)
    if isinstance(items, list):
        log_integration_success(logger, "gnews", items=len(items), query=q_text)
    else:
        log_integration_warning(
            logger, "gnews", reason="unexpected_response_shape", query=q_text
        )

    return items

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
    api_key = current_app.config.get("NEWSAPI_AI_API_KEY")
    if not api_key:
        log_integration_warning(logger, "newsapi_ai", reason="no_api_key")
        return []

    q_text = q_obj.get("query", "")

    log_integration_start(logger, "newsapi_ai", query=q_text)
    time.sleep(2.5)
    session = _get_session()

    query_obj = {
        "$query": _parse_to_er_query(q_text)
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

    items = map_newsapi_ai(data)
    if isinstance(items, list):
        log_integration_success(logger, "newsapi_ai", items=len(items), query=q_text)
    else:
        log_integration_warning(
            logger, "newsapi_ai", reason="unexpected_response_shape", query=q_text
        )

    return items




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
    video_category_id = "28" if "electronics" in category.lower() else None

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

    items = map_youtube(data, region=region_code)

    if isinstance(items, list):
        log_integration_success(logger, "youtube", items=len(items), query=q_text)
    else:
        log_integration_warning(
            logger, "youtube", reason="unexpected_response_shape", query=q_text
        )

    return items


def fetch_reddit_query(q_obj, **kwargs):
    """
    Pure fetcher for Reddit.
    q_obj["query"] is the subreddit name or a search query.
    Always returns a list (never None).
    """
    try:
        import praw
    except ImportError as e:
        log_integration_warning(
            logger, "reddit", reason="praw_not_installed", error=str(e)
        )
        return []

    client_id = current_app.config.get("REDDIT_CLIENT_ID")
    client_secret = current_app.config.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        log_integration_warning(logger, "reddit", reason="no_api_credentials")
        return []

    sub_name = q_obj.get("query", "").replace("r/", "")

    log_integration_start(logger, "reddit", subreddit=sub_name)

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="nexora-bot/1.0",
        )

        subreddit = reddit.subreddit(sub_name)

        submissions = list(subreddit.hot(limit=15))

        items = map_reddit(submissions, sub_name)

        if items:
            log_integration_success(
                logger, "reddit", items=len(items), subreddit=sub_name
            )
        else:
            log_integration_warning(
                logger, "reddit", reason="empty_results", subreddit=sub_name
            )

        return items

    except Exception as e:
        log_integration_error(logger, "reddit", e, subreddit=sub_name, exc_info=True)
        return []
