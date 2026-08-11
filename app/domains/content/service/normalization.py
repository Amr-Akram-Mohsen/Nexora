import logging
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from app.shared.sanitizer import sanitize_text
from app.shared.dto.ingestion import EnrichedItemDTO, ArticleCreateDTO
logger = logging.getLogger(__name__)
ALLOWED_TAGS = ['p', 'br', 'b', 'strong', 'i', 'em', 'u', 's', 'del', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'figure', 'figcaption', 'div', 'span']
ALLOWED_ATTRS = {'a': ['href', 'title', 'target', 'rel'], 'img': ['src', 'alt', 'width', 'height', 'loading'], '*': ['class']}
_TRACKING_PARAMS = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'ref', 'source', 'mc_cid', 'mc_eid', 'fbclid', 'gclid', '_ga', 'cmpid', 'linkId', 'WT.mc_id'}
BLOCKED_DOMAINS = ['wsj.com', 'ft.com', 'bloomberg.com', 'in.investing.com', 'medium.com', 'za.investing.com', 'nytimes.com', 'thetimes.co.uk']
DATE_FORMATS = ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d %H:%M:%S', '%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S GMT']
def normalize_url(url: str) -> str:
    if not url:
        return ''
    try:
        parsed = urlparse(url.strip())
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in _TRACKING_PARAMS}
        clean_query = urlencode(clean_qs, doseq=True)
        return urlunparse(parsed._replace(query=clean_query, fragment=''))
    except Exception as e:
        logger.debug('[Normalization] URL normalisation failed for %s: %s', url[:80], e)
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
    if not html_str:
        return ''
    try:
        import bleach
        return bleach.clean(html_str, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True, strip_comments=True)
    except ImportError:
        return re.sub('<[^>]+>', ' ', html_str).strip()
def extract_image_url(data: dict) -> str | None:
    raw_image = data.get('image_url') or data.get('urlToImage') or data.get('image') or data.get('media_content')
    if not raw_image:
        return None
    if isinstance(raw_image, list) and raw_image:
        product = raw_image[0]
        url = product.get('url') if isinstance(product, dict) else str(product)
    elif isinstance(raw_image, dict):
        url = raw_image.get('url')
    else:
        url = raw_image
    return url if url and str(url).startswith('http') else None
def normalize_article_data(enriched: EnrichedItemDTO) -> ArticleCreateDTO | None:
    data = enriched.model_dump() if hasattr(enriched, 'model_dump') else dict(enriched)
    url = normalize_url(data.get('url') or data.get('link'))
    title = sanitize_text(data.get('title') or '')
    if not url or not title:
        return None
    if any((d in url for d in BLOCKED_DOMAINS)):
        return None
    if '[Removed]' in title or len(title) < 10:
        return None
    description = data.get('description') or ''
    data.update({'title': title, 'description': sanitize_text(description), 'url': url, 'image_url': extract_image_url(data), 'published_at': parse_date(data.get('publishedAt') or data.get('published_at') or data.get('published')), 'source_name': sanitize_text(data.get('source_name') or (data.get('source') or {}).get('name') or ''), 'content_html': sanitize_html(data.get('content_html') or data.get('content')), 'content_text': sanitize_text(data.get('content_text') or ''), 'body': sanitize_text(data.get('body') or ''), 'canonical_url': normalize_url(data.get('canonical_url'))})
    return ArticleCreateDTO(**data)
def normalize_video_data(raw: dict) -> dict | None:
    data = raw.copy()
    title = sanitize_text(data.get('title') or '')
    if not title or not data.get('external_id'):
        return None
    normalized_comments = []
    for c in data.get('video_comments') or []:
        snippet = c.get('snippet', {})
        top_level = snippet.get('topLevelComment', {}).get('snippet', {})
        if not top_level:
            continue
        normalized_comments.append({'external_id': c.get('id'), 'author_name': sanitize_text(top_level.get('authorDisplayName') or ''), 'author_channel_id': top_level.get('authorChannelId', {}).get('value') if isinstance(top_level.get('authorChannelId'), dict) else None, 'text': top_level.get('textDisplay') or '', 'like_count': top_level.get('likeCount', 0), 'reply_count': snippet.get('totalReplyCount', 0), 'published_at': parse_date(top_level.get('publishedAt')), 'updated_at': parse_date(top_level.get('updatedAt'))})
        normalized_comments[-1]['text'] = sanitize_html(normalized_comments[-1]['text'])
    data.update({'title': title, 'description': sanitize_text(data.get('description') or ''), 'published_at': parse_date(data.get('published_at')), 'channel_name': sanitize_text(data.get('channel_name') or ''), 'thumbnail_url': data.get('thumbnail_url'), 'duration_seconds': data.get('duration_seconds'), 'video_comments': normalized_comments})
    return data
def normalize_post_data(raw: dict) -> dict | None:
    data = raw.copy()
    if not data.get('external_id'):
        return None
    data.update({'title': sanitize_text(data.get('title') or ''), 'body': sanitize_text(data.get('body') or ''), 'published_at': parse_date(data.get('published_at')), 'author': sanitize_text(data.get('author') or '')})
    return data
def strip_html(html_str: str) -> str:
    if not html_str:
        return ''
    text = re.sub('<[^>]+>', ' ', html_str)
    return ' '.join(text.split())
def text_to_html(text: str) -> str:
    if not text:
        return ''
    parts = text.split('\n\n')
    return ''.join((f'<p>{p.strip()}</p>' for p in parts if p.strip()))
def normalize_content_shaping(html: str | None, text: str | None) -> dict:
    content_html = html or ''
    content_text = text or ''
    if content_html and (not content_text):
        content_text = strip_html(content_html)
    elif content_text and (not content_html):
        content_html = text_to_html(content_text)
    return {'content_html': content_html, 'content_text': content_text, 'word_count': len(content_text.split()) if content_text else 0}
def calculate_content_health_score(c, target, duplicate):
    score = 0
    if getattr(c, 'title', None):
        score += 10
    if getattr(c, 'preview_text', None) or getattr(target, 'description', None) or getattr(target, 'preview_text', None):
        score += 10
    if getattr(c, 'category', None) and getattr(c.category, 'slug', None) != 'uncategorized':
        score += 10
    has_topics = any((ce.entity.entity_type in ('topic', 'tag', 'concept') for ce in c.content_entities)) if hasattr(c, 'content_entities') else False
    has_brands = any((ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand' for ce in c.content_entities)) if hasattr(c, 'content_entities') else False
    if has_topics:
        score += 15
    if has_brands:
        score += 15
    if getattr(c, 'source_id', None):
        score += 10
    if not duplicate:
        score += 5
    if getattr(c, 'object_type', None) == 'article' and target:
        if getattr(target, 'is_content_scraped', False):
            score += 10
        if getattr(target, 'status', '') == 'complete':
            score += 10
        if getattr(target, 'quality_score', 0) > 0:
            score += 5
    elif getattr(c, 'object_type', None) in ('video', 'post'):
        score += 25
    return min(score, 100)