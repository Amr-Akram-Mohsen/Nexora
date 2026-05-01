# app/integrations/social/reddit.py
import logging
from datetime import datetime
from flask import current_app
from app.shared.constants.taxonomy import REDDIT_SUBREDDITS

logger = logging.getLogger(__name__)

MIN_SCORE = 20
MIN_LENGTH = 80

def fetch_reddit_query(q_obj: dict) -> list[dict]:
    """
    Pure fetcher for Reddit.
    q_obj here might represent a subreddit name or a search query.
    """
    try:
        import praw
    except ImportError:
        return []

    client_id     = current_app.config.get("REDDIT_CLIENT_ID")
    client_secret = current_app.config.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.warning("[Reddit] No API key")
        print("[Reddit] No API key")
        return []

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="nexora-bot/1.0",
        )
        
        # In the old logic, 'query' was often the subreddit name for Reddit
        sub_name = q_obj.get("query", "").replace("r/", "")
        subreddit = reddit.subreddit(sub_name)
        
        raw_items = []
        for submission in subreddit.hot(limit=20):
            if submission.score < MIN_SCORE: continue
            if submission.is_self and len(submission.selftext) < MIN_LENGTH: continue

            url = f"https://www.reddit.com{submission.permalink}"
            description = submission.selftext[:500] if submission.is_self else submission.url
            thumbnail = submission.thumbnail if submission.thumbnail.startswith("http") else None
            
            region_map = {"saudiarabia": "SA", "dubai": "AE", "abudhabi": "AE", "emirates": "AE"}
            region = region_map.get(sub_name.lower())

            raw_items.append({
                "title":        submission.title,
                "description":  description,
                "url":          url,
                "image_url":    thumbnail,
                "published_at": datetime.utcfromtimestamp(submission.created_utc),
                "source_name":  f"r/{sub_name}",
                "region":       region,
                "external_id":  submission.id,
                "platform":     "reddit"
            })
        return raw_items
    except Exception:
        logger.exception("[Reddit] Error fetching r/%s", q_obj.get("query"))
        return []

def fetch_all_reddit(limit: int | None = None) -> int:
    """Entry point refactored to use IngestionWorkflow."""
    from app.application.content.ingestion_workflow import run_orchestrated_ingestion
    
    # Reddit doesn't have a strict quota like NewsAPI, but we use can_call_func for consistency
    return run_orchestrated_ingestion(
        source_name="Reddit",
        object_type="post",
        fetcher_func=fetch_reddit_query,
        can_call_func=lambda: True, # No strict daily limit tracked yet
        record_call_func=lambda: None,
        source_filter="reddit",
        limit=limit,
        cooldown_hours=24
    )
