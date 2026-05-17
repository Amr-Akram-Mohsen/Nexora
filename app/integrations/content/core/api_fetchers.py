import logging
from flask import current_app
from app.shared.utils.logging import (
    log_integration_start,
    log_integration_success,
    log_integration_error,
    log_integration_warning,
)
from .http import _get_session
from .fetch_engine import safe_get_json
from .fetchers_mappers import map_newsapi, map_gnews, map_youtube, map_reddit

logger = logging.getLogger(__name__)


import time
import re


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

    data = safe_get_json(
        session,
        "https://newsapi.org/v2/everything",
        params={
            "q": q_text,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
            "apiKey": api_key,
        },
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

    _ARABIC_CHARS = set("ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي")

    q_text = q_obj.get("query", "")
    # Sanitize: '&' and special chars in category names break GNews URL parsing
    q_text = q_text.replace(" & ", " and ").replace("&", "and")
    # GNews uses '-' for the NOT operator, which can cause 400 Bad Requests.
    q_text = q_text.replace("-", " ")
    q_text = re.sub(r"[^\w\s\(\)\"\'OR]", " ", q_text)
    q_text = re.sub(r"\s+", " ", q_text).strip()
    country = q_obj.get("region", "sa").lower()
    lang = "ar" if any(c in q_text for c in _ARABIC_CHARS) else "en"

    log_integration_start(logger, "gnews", query=q_text, country=country, lang=lang)
    session = _get_session()

    data = safe_get_json(
        session,
        "https://gnews.io/api/v4/search",
        params={
            "q": q_text,
            "lang": lang,
            "country": country,
            "max": 10,
            "apikey": api_key,
        },
        timeout=(3.05, 10),
        logger=logger,
        source_name="gnews",
    )

    items = map_gnews(data, region=country)

    if isinstance(items, list):
        log_integration_success(logger, "gnews", items=len(items), query=q_text)
    else:
        log_integration_warning(
            logger, "gnews", reason="unexpected_response_shape", query=q_text
        )

    return items


def fetch_youtube_query(q_obj, **kwargs):
    api_key = current_app.config.get("YOUTUBE_API_KEY")
    if not api_key:
        log_integration_warning(logger, "youtube", reason="no_api_key")
        return []

    _ARABIC_CHARS = set("ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي")

    q_text = q_obj.get("query", "")
    region_code = q_obj.get("region", "SA")
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
