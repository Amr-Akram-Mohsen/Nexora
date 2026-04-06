# app/scrapers/cleaner.py
"""
Universal article cleaner.
Every source (RSS, NewsAPI, GNews, YouTube, Reddit) passes its raw data
through clean_article_data() before calling store_article().

The cleaner's job is normalisation and quality filtering only.
It does NOT make decisions about category, brand, or section —
those come from the scraper's query context and are passed through as-is.

Input dict keys accepted (any source):
  title, description, url, image_url, published_at,
  source_name, section_slug,
  category_slug,          ← set by the scraper, passed through unchanged
  brand_slugs,            ← list of brand slugs, passed through unchanged
  topic_slugs,            ← list of topic slugs, passed through unchanged

Returns a normalised dict OR None (skipped article).
"""
import re
import html
from datetime import datetime
from app.utils.sanitizer import sanitize_text

# ── Blocked domains (paywalled / very low quality) ─────────────
BLOCKED_DOMAINS = [
    "wsj.com", "ft.com", "bloomberg.com",
    "nytimes.com", "thetimes.co.uk",
]

# ── Date format strings to attempt when parsing string dates ───
DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S GMT",
]


def _is_blocked(url: str) -> bool:
    return any(domain in url for domain in BLOCKED_DOMAINS)


def _parse_date(value) -> datetime | None:
    """Accept a datetime / struct_time / string and return a naive UTC datetime."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    # feedparser gives time.struct_time — handled upstream in rss_fetcher
    if not isinstance(value, str) or not value.strip():
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=None)
        except ValueError:
            continue
    return None


def _clean_description(text: str | None) -> str:
    if not text:
        return ""
    # NewsAPI truncates with "… [+XXXX chars]" — strip that
    if "… [+" in text:
        text = text.split("… [+")[0].strip()
    return sanitize_text(text)


def clean_article_data(raw: dict, section_slug: str) -> dict | None:
    """
    Normalise a raw article dict from any source.
    Returns None if the article fails quality checks.

    The caller (scraper) supplies section_slug as a positional arg,
    and may also include category_slug / brand_slugs / topic_slugs
    inside `raw` — these are passed through untouched.
    """
    # ── Mandatory fields ────────────────────────────────────────
    url = (raw.get("url") or raw.get("link") or "").strip()
    title = sanitize_text(raw.get("title") or "")

    if not url or not title:
        return None
    if _is_blocked(url):
        return None
    if "[Removed]" in title:      # NewsAPI removed/paywalled articles
        return None
    if len(title) < 10:
        return None

    # ── Description ─────────────────────────────────────────────
    description = _clean_description(
        raw.get("description")
        or raw.get("summary")
        or raw.get("selftext")   # Reddit self-posts
        or ""
    )

    # ── Image URL ────────────────────────────────────────────────
    image_url = (
        raw.get("urlToImage")        # NewsAPI
        or raw.get("image_url")      # internal / GNews uses "image"
        or raw.get("image")          # GNews
        or raw.get("media_content")  # some RSS feeds
        or None
    )
    if image_url and not str(image_url).startswith("http"):
        image_url = None

    # ── Date ─────────────────────────────────────────────────────
    published_at = _parse_date(
        raw.get("publishedAt")    # NewsAPI
        or raw.get("published_at")
        or raw.get("published")   # GNews
    ) or datetime.utcnow()

    # ── Source name ──────────────────────────────────────────────
    source_raw = (
        raw.get("source_name")
        or (raw.get("source") or {}).get("name")  # NewsAPI: {"source":{"name":...}}
        or raw.get("channelTitle")                 # YouTube
        or ""
    )
    source_name = sanitize_text(source_raw)

    return {
        # ── Core fields ──────────────────────────────────────────
        "title":         title,
        "description":   description,
        "url":           url,
        "image_url":     image_url,
        "published_at":  published_at,
        "source_name":   source_name,
        # ── Taxonomy (set by scraper, passed through as-is) ──────
        "section_slug":  section_slug,
        "category_slug": raw.get("category_slug") or "",
        "brand_slugs":   raw.get("brand_slugs") or [],
        "topic_slugs":   raw.get("topic_slugs") or [],
    }
