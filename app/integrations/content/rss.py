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

def fetch_rss_query(q_obj: dict, **kwargs) -> list[dict]:
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
