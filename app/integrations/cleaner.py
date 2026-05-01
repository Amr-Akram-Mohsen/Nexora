# app/integrations/cleaner.py
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
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from app.shared.sanitizer import sanitize_text
import logging
logger = logging.getLogger(__name__)
# ── Safe HTML tags allowed in article content ──────────────────
# Everything else is stripped. Script/style/iframe always removed.
ALLOWED_TAGS = [
    "p", "br", "b", "strong", "i", "em", "u", "s", "del",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "a", "img",
    "blockquote", "pre", "code",
    "table", "thead", "tbody", "tr", "th", "td",
    "figure", "figcaption",
    "div", "span",
]
ALLOWED_ATTRS = {
    "a":   ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height", "loading"],
    "*":   ["class"],
}

# Tracking query params to strip from article URLs for deduplication
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "ref", "source", "mc_cid", "mc_eid", "fbclid", "gclid", "_ga",
    "cmpid", "linkId", "WT.mc_id",
}

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


def _normalize_url(url: str) -> str:
    """
    Strip tracking params and URL fragments so the same article from
    different sources/campaigns is recognized as a duplicate.
    """
    try:
        parsed = urlparse(url.strip())
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in _TRACKING_PARAMS}
        clean_query = urlencode(clean_qs, doseq=True)
        # Also strip URL fragment (#section) — doesn't affect content identity
        return urlunparse(parsed._replace(query=clean_query, fragment=""))
    except Exception:
        return url


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


def _sanitize_content(html_str: str) -> str:
    """
    Sanitize HTML content: allow safe tags (p, h2, ul, img, a, etc.),
    strip everything else including scripts, iframes, and style blocks.
    Uses bleach if available; falls back to stripping all tags.
    """
    if not html_str:
        return ""
    try:
        import bleach
        return bleach.clean(
            html_str,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRS,
            strip=True,
            strip_comments=True,
        )
    except ImportError:
        # bleach not installed: safely strip ALL tags as fallback
        return re.sub(r"<[^>]+>", " ", html_str).strip()


def _clean_description(text: str | None) -> str:
    if not text:
        return ""
    # NewsAPI truncates with "… [+XXXX chars]" — strip that
    if "… [+" in text:
        text = text.split("… [+")[0].strip()
    return sanitize_text(text)


def clean_article_data(raw: dict, skip_scrape: bool = False) -> dict | None:
    """
    Normalise a raw article dict from any source.
    Returns None if the article fails quality checks.
    
    Responsibility: Normalization, sanitization, formatting, basic validation ONLY.
    """
    # ── Mandatory fields ────────────────────────────────────────
    url_raw = (raw.get("url") or raw.get("link") or "").strip()
    url = _normalize_url(url_raw)  # strip tracking params + fragments for dedup
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

    # ── Content (Sanitize only, no scraping) ─────────────────────
    content = raw.get("content")
    if content:
        content = _sanitize_content(content)

    return {
        "title":              title,
        "description":        description,
        "content":            content,
        "url":                url,
        "image_url":          image_url,
        "published_at":       published_at,
        "source_name":        source_name,

        # Pass-through classification (CRITICAL)
        "section_slug": raw.get("section_slug"),
        "category_slug": raw.get("category_slug"),
        "topic_slugs": raw.get("topic_slugs", []),
        "brand_slugs": raw.get("brand_slugs", []),
        "facets": raw.get("facets", {}),
    }
