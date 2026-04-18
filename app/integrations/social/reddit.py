# app/scrapers/reddit_fetcher.py
"""
Reddit PRAW fetcher — community layer (real user opinions).
Structure: { section_slug: { category_slug: [subreddits] } }
"""
import logging
from datetime import datetime
from flask import current_app
from app.integrations.cleaner import clean_article_data
from app.domains.article.storage import store_article

logger = logging.getLogger(__name__)

# ── Subreddit Registry ────────────────────────────────────────────
SUBREDDITS = {
    "community": {
        "electronics": ["gadgets", "smartphones", "Android", "iphone", "hardware"],
        "perfumes":    ["fragrance", "malefragrance", "feminineFragrance", "oud"],
        "accessories": ["Watches", "streetwear", "malefashionadvice"],
        "regional":    ["saudiarabia", "dubai", "abudhabi", "emirates"], # Regional is separate
    }
}

MIN_SCORE = 20    # Quality threshold
MIN_LENGTH = 80   # Skip short posts (chars)


def fetch_subreddit(name: str, section_slug: str, category_slug: str, limit: int = 20) -> int:
    """Fetch hot posts from a subreddit and store as articles."""
    try:
        import praw
    except ImportError:
        logger.warning("[Reddit] praw not installed")
        return 0

    client_id     = current_app.config.get("REDDIT_CLIENT_ID")
    client_secret = current_app.config.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        return 0

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="nexora-bot/1.0",
        )
        subreddit = reddit.subreddit(name)
        stored = 0

        for submission in subreddit.hot(limit=limit):
            if submission.score < MIN_SCORE:
                continue
            if submission.is_self and len(submission.selftext) < MIN_LENGTH:
                continue

            url = f"https://www.reddit.com{submission.permalink}"
            description = (
                submission.selftext[:500] if submission.is_self
                else submission.url
            )
            thumbnail = submission.thumbnail if submission.thumbnail.startswith("http") else None

            raw = {
                "title":        submission.title,
                "description":  description,
                "url":          url,
                "image_url":    thumbnail,
                "published_at": datetime.utcfromtimestamp(submission.created_utc),
                "source_name":  f"r/{name}",
                "section_slug": section_slug,
                "category_slug": category_slug if category_slug != "regional" else "general",
            }
            cleaned = clean_article_data(raw)
            if cleaned and store_article(cleaned):
                stored += 1
        return stored
    except Exception:
        logger.exception("[Reddit] Error fetching r/%s", name)
        return 0


def fetch_all_reddit() -> int:
    total = 0
    section_slug = "community"
    categories = SUBREDDITS.get(section_slug, {})
    
    for category_slug, sub_list in categories.items():
        for sub in sub_list:
            logger.info("[Reddit] Fetching r/%s (%s)", sub, category_slug)
            count = fetch_subreddit(sub, section_slug, category_slug)
            total += count
            logger.info("[Reddit]   -> %d posts stored", count)
    return total
