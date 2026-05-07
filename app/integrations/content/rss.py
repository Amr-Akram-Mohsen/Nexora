# app/integrations/content/rss.py
import logging
from datetime import datetime
import feedparser
from app.shared.utils.logging import log_integration_start, log_integration_success, log_integration_error

logger = logging.getLogger(__name__)

_NAME = "rss"

# Feed Registry
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
    },
}


def _extract_content(entry) -> str:
    if hasattr(entry, "content") and isinstance(entry.content, list):
        for c in entry.content:
            val = c.get("value", "")
            if val and len(val) > 100:
                return val
    summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
    return summary if len(summary) > 500 else ""


def fetch_rss_query(q_obj: dict, **kwargs) -> list[dict]:
    """
    Pure fetcher for a single RSS feed URL.
    q_obj["query"] here is the feed URL.
    Always returns a list (never None).
    """
    feed_url = q_obj.get("query", "")
    if not feed_url:
        logger.warning("[INTEGRATION][%s] skipped  reason=no_feed_url", _NAME)
        return []

    log_integration_start(logger, _NAME, url=feed_url)

    try:
        feed = feedparser.parse(feed_url, agent="NexoraBot/1.0")

        if not feed.entries:
            logger.info("[INTEGRATION][%s] empty feed  url=%s", _NAME, feed_url)
            return []

        source_name = feed.feed.get("title") or feed_url
        raw_items = []
        for entry in feed.entries[:30]:
            url = getattr(entry, "link", None)
            title = getattr(entry, "title", None)
            if not url or not title:
                continue

            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    pub_date = datetime(*entry.published_parsed[:6])
                except (TypeError, ValueError) as date_err:
                    logger.debug("[INTEGRATION][%s] date parse failed  url=%s  err=%s", _NAME, url, date_err)

            raw_items.append({
                "title":        title,
                "description":  getattr(entry, "summary", "") or getattr(entry, "description", ""),
                "content":      _extract_content(entry),
                "url":          url,
                "published_at": pub_date,
                "source_name":  source_name,
            })

        log_integration_success(logger, _NAME, items=len(raw_items), url=feed_url)
        return raw_items

    except Exception as e:
        log_integration_error(logger, _NAME, e, url=feed_url)
        return []
