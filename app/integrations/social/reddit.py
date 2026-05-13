# app/integrations/social/reddit.py
import logging
from datetime import datetime
from flask import current_app
from app.shared.utils.logging import log_integration_start, log_integration_success, log_integration_error, log_integration_warning

logger = logging.getLogger(__name__)

_NAME = "reddit"
MIN_SCORE = 20
MIN_LENGTH = 80

_REGION_MAP = {
    "saudiarabia": "SA",
    "dubai": "AE",
    "abudhabi": "AE",
    "emirates": "AE",
}


def fetch_reddit_query(q_obj: dict, **kwargs) -> list[dict]:
    """
    Pure fetcher for Reddit.
    q_obj["query"] is the subreddit name or a search query.
    Always returns a list (never None).
    """
    try:
        import praw
    except ImportError as e:
        log_integration_warning(logger, _NAME, reason="praw_not_installed", error=str(e))
        return []

    client_id     = current_app.config.get("REDDIT_CLIENT_ID")
    client_secret = current_app.config.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        log_integration_warning(logger, _NAME, reason="no_api_credentials")
        return []

    sub_name = q_obj.get("query", "").replace("r/", "")
    log_integration_start(logger, _NAME, subreddit=sub_name)

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="nexora-bot/1.0",
        )

        subreddit = reddit.subreddit(sub_name)

        raw_items = []
        from app.shared.dto.ingestion import RawItemDTO
        for submission in subreddit.hot(limit=20):
            if submission.score < MIN_SCORE:
                continue
            if submission.is_self and len(submission.selftext) < MIN_LENGTH:
                continue

            url = f"https://www.reddit.com{submission.permalink}"
            description = submission.selftext[:500] if submission.is_self else submission.url
            thumbnail = submission.thumbnail if submission.thumbnail.startswith("http") else None
            region = _REGION_MAP.get(sub_name.lower())

            raw_items.append(RawItemDTO(
                title=submission.title,
                body=description,
                url=url,
                image_url=thumbnail,
                published_at=datetime.utcfromtimestamp(submission.created_utc),
                author=str(submission.author),
                subreddit=sub_name,
                upvotes=submission.score,
                comments_count=submission.num_comments,
                region=region,
                external_id=submission.id,
                platform="reddit",
            ))

        log_integration_success(logger, _NAME, items=len(raw_items), subreddit=sub_name)
        return raw_items

    except Exception as e:
        log_integration_error(logger, _NAME, e, subreddit=sub_name, exc_info=True)
        return []
