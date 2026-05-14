# app/integrations/content/article_utils/cleaner.py
"""
Specialized content cleaners for Articles, Videos, and Posts.
Approach: Modify a copy of raw data only where cleaning is required.
Ensures 1:1 alignment with Domain Models.
"""

import logging
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from app.shared.sanitizer import sanitize_text
from app.shared.dto.ingestion import EnrichedItemDTO, ArticleCreateDTO

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────
ALLOWED_TAGS = [
    "p",
    "br",
    "b",
    "strong",
    "i",
    "em",
    "u",
    "s",
    "del",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "a",
    "img",
    "blockquote",
    "pre",
    "code",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "figure",
    "figcaption",
    "div",
    "span",
]
ALLOWED_ATTRS = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height", "loading"],
    "*": ["class"],
}

_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "ref",
    "source",
    "mc_cid",
    "mc_eid",
    "fbclid",
    "gclid",
    "_ga",
    "cmpid",
    "linkId",
    "WT.mc_id",
}

BLOCKED_DOMAINS = [
    "wsj.com",
    "ft.com",
    "bloomberg.com",
    "nytimes.com",
    "thetimes.co.uk",
]

DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S GMT",
]


# ── Shared Utility Helpers ───────────────────────────────────────
def _normalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in _TRACKING_PARAMS}
        clean_query = urlencode(clean_qs, doseq=True)
        return urlunparse(parsed._replace(query=clean_query, fragment=""))
    except Exception as e:
        logger.debug("[CLEANER] url_norm_failed  url=%s  err=%s", url[:80], e)
        return url


def _parse_date(value) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if not isinstance(value, str) or not value.strip():
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=None)
        except ValueError:
            continue
    return None


def _sanitize_content(html_str: str) -> str:
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
        return re.sub(r"<[^>]+>", " ", html_str).strip()


class DomainMapper:
    @staticmethod
    def to_article_dto(
        enriched: EnrichedItemDTO, skip_scrape: bool = False
    ) -> ArticleCreateDTO | None:
        """Standardizes news article fields for the Article model."""
        data = (
            enriched.model_dump() if hasattr(enriched, "model_dump") else dict(enriched)
        )

        url = _normalize_url(data.get("url") or data.get("link"))
        title = sanitize_text(data.get("title") or "")

        if not url or not title:
            return None
        if any(d in url for d in BLOCKED_DOMAINS):
            return None
        if "[Removed]" in title or len(title) < 10:
            return None

        description = data.get("description") or data.get("summary") or ""
        if "… [+" in description:
            description = description.split("… [+")[0].strip()

        # Robust image extraction (handles strings, lists, or dicts from various APIs/RSS)
        raw_image = (
            data.get("image_url")
            or data.get("urlToImage")
            or data.get("image")
            or data.get("media_content")
        )
        image_url = None

        if isinstance(raw_image, list) and raw_image:
            item = raw_image[0]
            image_url = item.get("url") if isinstance(item, dict) else str(item)
        elif isinstance(raw_image, dict):
            image_url = raw_image.get("url")
        else:
            image_url = raw_image

        if image_url and not str(image_url).startswith("http"):
            image_url = None

        published_at = _parse_date(
            data.get("publishedAt") or data.get("published_at") or data.get("published")
        )
        source_name = sanitize_text(
            data.get("source_name") or (data.get("source") or {}).get("name") or ""
        )

        data.update(
            {
                "title": title,
                "description": sanitize_text(description),
                "url": url,
                "image_url": image_url,
                "published_at": published_at or datetime.utcnow(),
                "source_name": source_name,
                "content": _sanitize_content(data.get("content")),
            }
        )
        return ArticleCreateDTO(**data)


# ── 2. Video Cleaner (YouTube) ───────────────────────────────────
def clean_video_data(raw: dict) -> dict | None:
    """Aligns YouTube item with the Video model."""
    data = raw.copy()

    title = sanitize_text(data.get("title") or "")
    if not title or not data.get("external_id"):
        return None

    data.update(
        {
            "title": title,
            "description": sanitize_text(data.get("description") or ""),
            "published_at": _parse_date(data.get("published_at")) or datetime.utcnow(),
            "channel_name": sanitize_text(data.get("channel_name") or ""),
            "thumbnail_url": data.get("thumbnail_url"),
            "content": None,
        }
    )
    return data


# ── 3. Post Cleaner (Reddit) ─────────────────────────────────────
def clean_post_data(raw: dict) -> dict | None:
    """Aligns Reddit submission with the Post model."""
    data = raw.copy()

    if not data.get("external_id"):
        return None

    data.update(
        {
            "title": sanitize_text(data.get("title") or ""),
            "body": sanitize_text(data.get("body") or ""),
            "published_at": _parse_date(data.get("published_at")) or datetime.utcnow(),
            "author": sanitize_text(data.get("author") or ""),
            "content": None,
        }
    )
    return data
