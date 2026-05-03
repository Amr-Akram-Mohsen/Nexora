# app/integrations/social/reddit.py
import logging
from datetime import datetime
from flask import current_app
from app.shared.constants.taxonomy import REDDIT_SUBREDDITS

logger = logging.getLogger(__name__)

MIN_SCORE = 20
MIN_LENGTH = 80

def fetch_reddit_query(q_obj: dict, **kwargs) -> list[dict]:
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
                "title":          submission.title,
                "body":           description, # Normalized Reddit text
                "url":            url,
                "image_url":      thumbnail,
                "published_at":   datetime.utcfromtimestamp(submission.created_utc),
                "author":         str(submission.author),
                "subreddit":      sub_name,
                "upvotes":        submission.score,
                "comments_count": submission.num_comments,
                "region":         region,
                "external_id":    submission.id,
                "platform":       "reddit"
            })
        return raw_items
    except Exception:
        logger.exception("[Reddit] Error fetching r/%s", q_obj.get("query"))
        return []
