# app/domains/content/service/normalization.py
import logging
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from app.shared.sanitizer import sanitize_text
from app.shared.dto.ingestion import EnrichedItemDTO, ArticleCreateDTO

logger = logging.getLogger(__name__)

# --- Configuration Constants ---
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
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "ref", "source", "mc_cid", "mc_eid", "fbclid", "gclid", "_ga",
    "cmpid", "linkId", "WT.mc_id",
}
BLOCKED_DOMAINS = ["wsj.com", "ft.com", "bloomberg.com", "nytimes.com", "thetimes.co.uk"]
DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S GMT",
]

# --- Core Utility Functions ---

def normalize_url(url: str) -> str:
    if not url: return ""
    try:
        parsed = urlparse(url.strip())
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in _TRACKING_PARAMS}
        clean_query = urlencode(clean_qs, doseq=True)
        return urlunparse(parsed._replace(query=clean_query, fragment=""))
    except Exception as e:
        logger.debug("[Normalization] URL normalisation failed for %s: %s", url[:80], e)
        return url

def parse_date(value) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if not isinstance(value, str) or not value.strip():
        return datetime.utcnow()
        
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=None)
        except ValueError:
            continue
    return datetime.utcnow()

def sanitize_html(html_str: str) -> str:
    if not html_str: return ""
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

def extract_image_url(data: dict) -> str | None:
    raw_image = (data.get("image_url") or data.get("urlToImage") or data.get("image") or data.get("media_content"))
    if not raw_image: return None
    
    if isinstance(raw_image, list) and raw_image:
        item = raw_image[0]
        url = item.get("url") if isinstance(item, dict) else str(item)
    elif isinstance(raw_image, dict):
        url = raw_image.get("url")
    else:
        url = raw_image

    return url if url and str(url).startswith("http") else None

# --- Main Service Functions ---

def normalize_article_data(enriched: EnrichedItemDTO) -> ArticleCreateDTO | None:
    """Consolidated logic for mapping any raw article data to the domain model."""
    data = enriched.model_dump() if hasattr(enriched, "model_dump") else dict(enriched)
    
    url = normalize_url(data.get("url") or data.get("link"))
    title = sanitize_text(data.get("title") or "")
    
    if not url or not title: return None
    if any(d in url for d in BLOCKED_DOMAINS): return None
    if "[Removed]" in title or len(title) < 10: return None

    description = data.get("description") or ""

    data.update({
        "title":          title,
        "description":    sanitize_text(description),
        "url":            url,
        "image_url":      extract_image_url(data),
        "published_at":   parse_date(data.get("publishedAt") or data.get("published_at") or data.get("published")),
        "source_name":    sanitize_text(data.get("source_name") or (data.get("source") or {}).get("name") or ""),
        "content_html":   sanitize_html(data.get("content_html") or data.get("content")),
        "content_text":   sanitize_text(data.get("content_text") or ""),
        "canonical_url":  normalize_url(data.get("canonical_url"))
    })
    
    return ArticleCreateDTO(**data)

def normalize_video_data(raw: dict) -> dict | None:
    data = raw.copy()
    title = sanitize_text(data.get("title") or "")
    if not title or not data.get("external_id"): return None

    data.update({
        "title":          title,
        "description":    sanitize_text(data.get("description") or ""),
        "published_at":   parse_date(data.get("published_at")),
        "channel_name":   sanitize_text(data.get("channel_name") or ""),
        "thumbnail_url":  data.get("thumbnail_url"),
    })
    return data

def normalize_post_data(raw: dict) -> dict | None:
    data = raw.copy()
    if not data.get("external_id"): return None

    data.update({
        "title":          sanitize_text(data.get("title") or ""),
        "body":           sanitize_text(data.get("body") or ""),
        "published_at":   parse_date(data.get("published_at")),
        "author":         sanitize_text(data.get("author") or ""),
    })
    return data

# --- View Serialization ---

def strip_html(html_str: str) -> str:
    if not html_str: return ""
    text = re.sub(r"<[^>]+>", " ", html_str)
    return " ".join(text.split())

def text_to_html(text: str) -> str:
    if not text: return ""
    parts = text.split("\n\n")
    return "".join(f"<p>{p.strip()}</p>" for p in parts if p.strip())

def normalize_content_shaping(html: str | None, text: str | None) -> dict:
    """Ensures both HTML and text formats are present and computes word count."""
    content_html = html or ""
    content_text = text or ""
    
    if content_html and not content_text:
        content_text = strip_html(content_html)
    elif content_text and not content_html:
        content_html = text_to_html(content_text)
        
    return {
        "content_html": content_html,
        "content_text": content_text,
        "word_count": len(content_text.split()) if content_text else 0
    }


