# app/scrapers/reddit_fetcher.py
"""
Reddit PRAW fetcher — community layer (real user opinions).
Structure: { section_slug: { category_slug: [subreddits] } }
"""
import logging
from datetime import datetime
from flask import current_app
from app.integrations.external.api import should_refetch, mark_fetched
from app.integrations.exceptions import (
    PipelineFatalError, PipelineQuotaExceededError
)

logger = logging.getLogger(__name__)

from app.shared.constants.taxonomy import REDDIT_SUBREDDITS

MIN_SCORE = 20    # Quality threshold
MIN_LENGTH = 80   # Skip short posts (chars)


def fetch_subreddit(name: str, section_slug: str, category_slug: str, limit: int = 20) -> int:
    """Fetch hot posts from a subreddit and store as articles."""
    # 1. Check Cooldown
    cache_key = f"reddit:{name}"
    if not should_refetch(section_slug, cache_key, hours=24):
        return 0

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

        # 2. Mark Fetched
        mark_fetched(
            section_slug, 
            cache_key, 
            category=category_slug, 
            source="reddit", 
            normalized_query=f"r/{name}"
        )

        print(f"  [Reddit] Fetching r/{name} ({category_slug})...")
        logger.info(f"[Reddit] Subreddit: r/{name}, Category: {category_slug}")

        from app.domains.content.ingestion import ingest_article_stream
        for submission in subreddit.hot(limit=limit):
            try:
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

                # Identify region for local subreddits
                region_map = {"saudiarabia": "SA", "dubai": "AE", "abudhabi": "AE", "emirates": "AE"}
                region = region_map.get(name.lower())

                raw = {
                    "title":        submission.title,
                    "description":  description,
                    "url":          url,
                    "image_url":    thumbnail,
                    "published_at": datetime.utcfromtimestamp(submission.created_utc),
                    "source_name":  f"r/{name}",
                    "section_slug": section_slug,
                    "category_slug": category_slug if category_slug != "regional" else "general",
                    "region":       region
                }
                
                from app.shared.constants.query_builder import CATEGORY_TOPIC_MAP, SECTION_DEFAULT_INTENTS
                from app.integrations.enrichment.pipeline import prepare_article
                
                # Mock q_obj for Reddit enrichment
                q_obj = {
                    "topics": CATEGORY_TOPIC_MAP.get(category_slug, []),
                    "brands": [],
                    "intent": SECTION_DEFAULT_INTENTS.get(section_slug, ["Discussion"])[0],
                    "region": region,
                    "query": f"r/{name}"
                }

                raw = prepare_article(raw, section_slug, category_slug, q_obj)

                from app.domains.content.ingestion import ingest_content
                from app.core.extensions import db
                raw["external_id"] = submission.id # submission.id, not post_id
                
                try:
                    if ingest_content(db.session, object_type="post", raw_data=raw):
                        stored += 1
                except Exception as e:
                    logger.critical("[Reddit] FATAL: Database insertion failed. Pipeline stopping.")
                    raise PipelineFatalError(f"Database insertion failed: {str(e)}") from e
            except PipelineFatalError:
                raise
            except Exception:
                logger.exception("[Reddit] Unexpected error processing submission in r/%s", name)

        if stored > 0:
            print(f"    -> [Reddit] Stored {stored} new posts from r/{name}")
            
        return stored
    except (PipelineFatalError, PipelineQuotaExceededError):
        raise
    except Exception:
        logger.exception("[Reddit] Error fetching r/%s", name)
        return 0


def fetch_all_reddit(limit: int | None = None) -> int:
    total = 0
    discovery_tasks = []
    for section_slug, categories in REDDIT_SUBREDDITS.items():
        for category_slug, sub_list in categories.items():
            for sub in sub_list:
                discovery_tasks.append((sub, section_slug, category_slug))

    if not discovery_tasks:
        return 0

    import random
    if limit:
        random.shuffle(discovery_tasks)
        discovery_tasks = discovery_tasks[:limit]

    logger.info("[Reddit] Starting discovery run with %d subreddits (Diverse Sample)", len(discovery_tasks))

    for sub, section, category in discovery_tasks:
        count = fetch_subreddit(sub, section, category)
        total += count
        
    return total
