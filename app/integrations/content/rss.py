# app/integrations/content/rss.py
import logging
from datetime import datetime
import feedparser

logger = logging.getLogger(__name__)

# Feed Registry (Same as before, truncated for brevity in this refactor)
RSS_FEEDS = {
    "reviews": {
        "electronics": ["https://www.gsmarena.com/rss-news-reviews.php3", "https://www.techradar.com/rss"],
        "perfumes": ["https://cafleurebon.com/feed/"],
        "accessories": ["https://www.ablogtowatch.com/feed/"],
    },
    "news": {
        "electronics": ["https://www.theverge.com/rss/index.xml"],
        "perfumes": ["https://perfumerflavorist.com/feed/"],
        "accessories": ["https://hypebeast.com/feed"],
    }
}

def _extract_content(entry) -> str:
    if hasattr(entry, "content") and isinstance(entry.content, list):
        for c in entry.content:
            val = c.get("value", "")
            if val and len(val) > 100: return val
    summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
    return summary if len(summary) > 500 else ""

def fetch_rss_query(q_obj: dict) -> list[dict]:
    """
    Pure fetcher for a single RSS feed URL.
    q_obj["query"] here is the feed URL.
    """
    feed_url = q_obj["query"]
    try:
        feed = feedparser.parse(feed_url, agent='NexoraBot/1.0')
        if not feed.entries: return []
        
        source_name = feed.feed.get("title") or feed_url
        raw_items = []
        for entry in feed.entries[:30]:
            url = getattr(entry, "link", None)
            title = getattr(entry, "title", None)
            if not url or not title: continue

            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6])

            raw_items.append({
                "title":        title,
                "description":  getattr(entry, "summary", "") or getattr(entry, "description", ""),
                "content":      _extract_content(entry),
                "url":          url,
                "published_at": pub_date,
                "source_name":  source_name
            })
        return raw_items
    except Exception:
        logger.warning("[RSS] Failed feed: %s", feed_url)
        return []

def fetch_all_rss(limit: int | None = None) -> int:
    """Entry point refactored to use IngestionWorkflow."""
    from app.application.content.ingestion_workflow import run_orchestrated_ingestion
    
    # Flatten the static RSS_FEEDS into query objects for the workflow
    flat_queries = []
    for section, categories in RSS_FEEDS.items():
        for category, feeds in categories.items():
            for f in feeds:
                flat_queries.append({
                    "query": f, 
                    "section": section, 
                    "category": category,
                    "topics": [],
                    "brands": [],
                    "intent": "News" if section == "news" else "Review"
                })

    # Since RSS feeds are static URLs, we bypass DiscoveryManager's section-based registry
    # and call run_orchestrated_ingestion with a manual task list if necessary.
    # For now, let's keep the logic aligned with the workflow's expectations.
    
    # We use run_orchestrated_ingestion but need to ensure it can handle 
    # manually provided queries if we modify it, or just use the pattern here.
    
    from app.application.content.ingestion_workflow import run_orchestrated_ingestion
    
    # Note: run_orchestrated_ingestion currently calls discovery.get_queries_by_section.
    # I will modify run_orchestrated_ingestion to accept optional 'queries' to be more flexible.
    
    return run_orchestrated_ingestion(
        source_name="RSS",
        object_type="article",
        fetcher_func=fetch_rss_query,
        can_call_func=lambda: True, # RSS has no strict API quota
        record_call_func=lambda: None,
        source_filter="rss",
        limit=limit,
        cooldown_hours=4,
        manual_queries=flat_queries # Passing manual queries
    )
