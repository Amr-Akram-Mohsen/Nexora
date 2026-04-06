# app/scrapers/rss_fetcher.py
"""
RSS/Atom feed fetcher — Unified for Electronics, Perfumes, and Accessories.
No API key needed. Unlimited requests.

Structure: { section_slug: { category_slug: [urls] } }
"""
import logging
from datetime import datetime
import feedparser
from .cleaner import clean_article_data
from .storer import store_article

logger = logging.getLogger(__name__)

# ── Feed Registry ─────────────────────────────────────────────────
# Mapped by [Section] -> [Category] -> [List of URLs]
RSS_FEEDS = {
    "reviews": {
        "electronics": [
            "https://www.gsmarena.com/rss-news-reviews.php3",
            "https://www.notebookcheck.net/News.8.0.html?feed=rss",
            "https://www.techradar.com/rss",
            "https://www.slashgear.com/feed/",
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
        ],
        "perfumes": [
            "https://perfumerflavorist.com/feed/",
        ],
        "accessories": [
            "https://hypebeast.com/feed",
            "https://www.highsnobiety.com/feed/",
        ],
    },
    "tutorials": {
        "electronics": [
            "https://www.howtogeek.com/feed/",
            "https://realpython.com/atom.xml",
        ],
        "accessories": [
            "https://www.apetogentleman.com/feed/",
        ]
    }
}


def _parse_entry(entry, section_slug: str, category_slug: str, source_name: str) -> dict | None:
    """Convert a single feedparser entry into a raw dict for the cleaner."""
    url = getattr(entry, "link", None)
    title = getattr(entry, "title", None)
    if not url or not title:
        return None

    published_at = None
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            published_at = datetime(*entry.published_parsed[:6])
        except Exception:
            pass

    # Extract image
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

    description = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""

    return {
        "title": title,
        "description": description,
        "url": url,
        "image_url": image_url,
        "published_at": published_at,
        "source_name": source_name,
        "section_slug": section_slug,
        "category_slug": category_slug,
    }


def fetch_rss_section_category(section_slug: str, category_slug: str, feed_urls: list[str]) -> int:
    stored = 0
    for feed_url in feed_urls:
        try:
            # Set User-Agent to avoid bot-blocking (Fragrantica, etc.)
            feed = feedparser.parse(feed_url, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            source_name = feed.feed.get("title", feed_url)

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
