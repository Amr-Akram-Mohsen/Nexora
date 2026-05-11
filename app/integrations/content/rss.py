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


def _extract_image_url(entry) -> str | None:
    """
    Extracts a featured image URL from various RSS namespaces.
    Supports Media RSS (media:content), enclosures, and standard links.
    """
    # 1. Media RSS (media:content) - Most reliable for tech sites
    media_content = entry.get("media_content", [])
    if media_content and isinstance(media_content, list):
        for media in media_content:
            url = media.get("url")
            if url and ("image" in media.get("type", "") or url.split("?")[0].lower().endswith((".jpg", ".jpeg", ".png", ".webp"))):
                return url

    # 2. Enclosures
    enclosures = entry.get("enclosures", [])
    if enclosures:
        for enc in enclosures:
            if "image" in enc.get("type", ""):
                return enc.get("href")

    # 3. Links (rel="enclosure")
    links = entry.get("links", [])
    if links:
        for link in links:
            if link.get("rel") == "enclosure" and "image" in link.get("type", ""):
                return link.get("href")

    # 4. Fallback: media:thumbnail
    if "media_thumbnail" in entry:
        thumbnails = entry.get("media_thumbnail", [])
        if thumbnails and isinstance(thumbnails, list):
            return thumbnails[0].get("url")

    return None


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

    # Support for Conditional GET
    etag = kwargs.get("etag")
    modified = kwargs.get("modified")

    try:
        feed = feedparser.parse(feed_url, etag=etag, modified=modified, agent="NexoraBot/1.0")

        # 304 Not Modified
        if feed.status == 304:
            logger.info("[INTEGRATION][%s] not modified  url=%s", _NAME, feed_url)
            return {"items": [], "etag": etag, "modified": modified}

        if not feed.entries:
            logger.info("[INTEGRATION][%s] empty feed or error  url=%s  status=%s", _NAME, feed_url, feed.status)
            return {"items": [], "etag": feed.get("etag"), "modified": feed.get("modified")}

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
                "image_url":    _extract_image_url(entry),
                "published_at": pub_date,
                "source_name":  source_name,
            })

        log_integration_success(logger, _NAME, items=len(raw_items), url=feed_url)
        return {
            "items": raw_items,
            "etag": feed.get("etag"),
            "modified": feed.get("modified")
        }

    except Exception as e:
        log_integration_error(logger, _NAME, e, url=feed_url)
        return []
