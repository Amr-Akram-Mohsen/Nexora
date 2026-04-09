# app/scrapers/rss_fetcher.py
"""
RSS/Atom feed fetcher — Unified for Electronics, Perfumes, and Accessories.
No API key needed. Unlimited requests.

Phase 6A improvements:
  - Extracts content:encoded (full article HTML from feeds that support it)
  - Skips dead/empty feeds gracefully with a warning, no crash
  - Normalizes URLs to strip common tracking params before storing (dedup)
  - Expanded with new free sources: Dev.to API, Hacker News, Product Hunt

Structure: { section_slug: { category_slug: [urls] } }
"""
import re
import logging
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import feedparser
from .cleaner import clean_article_data
from .storer import store_article

logger = logging.getLogger(__name__)

# Tracking query params to strip from article URLs before storing
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "ref", "source", "mc_cid", "mc_eid", "fbclid", "gclid", "_ga",
    "cmpid", "linkId", "WT.mc_id",
}

# ── Feed Registry ─────────────────────────────────────────────────
# Mapped by [Section] -> [Category] -> [List of URLs]
RSS_FEEDS = {
    "reviews": {
        "electronics": [
            "https://www.gsmarena.com/rss-news-reviews.php3",
            "https://www.notebookcheck.net/News.8.0.html?feed=rss",
            "https://www.techradar.com/rss",
            "https://www.slashgear.com/feed/",
            "https://arstechnica.com/gadgets/feed/",
            # Dev.to tech articles (full content, free, no key)
            "https://dev.to/feed/tag/programming",
            "https://dev.to/feed/tag/webdev",
        ],
        "perfumes": [
            "https://www.fragrantica.com/news/feed/",
            "https://cafleurebon.com/feed/",
        ],
        "accessories": [
            "https://www.ablogtowatch.com/feed/",
            "https://www.wristreview.com/feed/",
        ],
    },
    "news": {
        "electronics": [
            "https://www.theverge.com/rss/index.xml",
            "https://feeds.feedburner.com/TechCrunch/",
            "https://9to5google.com/feed/",
            "https://9to5mac.com/feed/",
            "https://www.engadget.com/rss.xml",
            "https://www.wired.com/feed/rss",
            # Hacker News top stories (discussion links, free, no key)
            "https://hnrss.org/frontpage",
            "https://hnrss.org/best",
        ],
        "perfumes": [
            "https://perfumerflavorist.com/feed/",
        ],
        "accessories": [
            "https://hypebeast.com/feed",
            "https://www.highsnobiety.com/feed/",
            # Product Hunt daily (new product launches)
            "https://www.producthunt.com/feed",
        ],
    },
    "tutorials": {
        "electronics": [
            "https://www.howtogeek.com/feed/",
            "https://www.digitaltrends.com/feed/",
            "https://www.androidauthority.com/feed/",
            # DEV Community tutorials (full content RSS, free)
            "https://dev.to/feed/tag/tutorial",
            "https://dev.to/feed/tag/javascript",
        ],
        "accessories": [
            "https://www.apetogentleman.com/feed/",
        ]
    }
}


def _strip_tracking_params(url: str) -> str:
    """Remove known tracking query parameters from a URL for cleaner deduplication."""
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in _TRACKING_PARAMS}
        clean_query = urlencode(clean_qs, doseq=True)
        return urlunparse(parsed._replace(query=clean_query))
    except Exception:
        return url


def _extract_content(entry) -> str:
    """
    Extract the fullest available content from a feed entry.
    Priority order:
      1. content:encoded (full HTML article body — most feeds that support it)
      2. entry.content list (Atom standard)
      3. entry.summary / description (fallback snippet)
    """
    # 1. content:encoded — feedparser exposes this as entry.content[0]
    #    when the feed uses <content:encoded> (WordPress, Dev.to, etc.)
    if hasattr(entry, "content") and isinstance(entry.content, list):
        for c in entry.content:
            val = c.get("value", "")
            if val and len(val) > 100:  # ignore empty/stub content blocks
                return val

    # 2. summary (most feeds provide at least a description here)
    summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""

    # 3. If summary is long enough to be a real body (>500 chars), use it as content too
    if len(summary) > 500:
        return summary

    return ""


def _parse_entry(entry, section_slug: str, category_slug: str, source_name: str) -> dict | None:
    """Convert a single feedparser entry into a raw dict for the cleaner."""
    url = getattr(entry, "link", None)
    title = getattr(entry, "title", None)
    if not url or not title:
        return None

    # Normalize URL to strip tracking params before dedup check
    url = _strip_tracking_params(url)

    published_at = None
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            published_at = datetime(*entry.published_parsed[:6])
        except Exception:
            pass

    # Extract image — try media_content, then enclosures
    image_url = None
    media = getattr(entry, "media_content", None)
    if media and isinstance(media, list) and media:
        image_url = media[0].get("url")
    if not image_url:
        enclosures = getattr(entry, "enclosures", [])
        for enc in enclosures:
            if enc.get("type", "").startswith("image"):
                image_url = enc.get("href")
                break
    # Try media:thumbnail as final fallback
    if not image_url:
        thumb = getattr(entry, "media_thumbnail", None)
        if thumb and isinstance(thumb, list):
            image_url = thumb[0].get("url")

    description = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
    content = _extract_content(entry)

    return {
        "title":        title,
        "description":  description,
        "content":      content,
        "url":          url,
        "image_url":    image_url,
        "published_at": published_at,
        "source_name":  source_name,
        "section_slug": section_slug,
        "category_slug": category_slug,
    }


def fetch_rss_section_category(section_slug: str, category_slug: str, feed_urls: list[str]) -> int:
    stored = 0
    for feed_url in feed_urls:
        try:
            feed = feedparser.parse(
                feed_url,
                agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            # Dead-feed detection: skip if feedparser got no entries and reported an error
            if feed.bozo and not feed.entries:
                logger.warning(
                    "[RSS] Dead/unreachable feed (bozo=%r): %s — skipping",
                    feed.bozo_exception.__class__.__name__ if hasattr(feed, 'bozo_exception') else True,
                    feed_url,
                )
                continue

            if not feed.entries:
                logger.info("[RSS] Empty feed (0 entries): %s", feed_url)
                continue

            source_name = feed.feed.get("title") or feed_url

            for entry in feed.entries[:15]:   # latest 15 per feed
                raw = _parse_entry(entry, section_slug, category_slug, source_name)
                if not raw:
                    continue
                cleaned = clean_article_data(raw, section_slug)
                if cleaned:
                    if store_article(cleaned):
                        stored += 1
        except Exception:
            logger.exception("[RSS] Failed to parse feed: %s", feed_url)
    return stored


def fetch_all_rss() -> int:
    total = 0
    for section_slug, categories in RSS_FEEDS.items():
        logger.info("[RSS] Fetching Section: %s", section_slug)
        for category_slug, feeds in categories.items():
            logger.info("[RSS]   Category: %s (%d feeds)", category_slug, len(feeds))
            count = fetch_rss_section_category(section_slug, category_slug, feeds)
            total += count
            logger.info("[RSS]     -> %d new articles stored", count)
    return total
