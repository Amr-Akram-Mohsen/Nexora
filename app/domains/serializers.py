from datetime import datetime
import re
from .serialization_utils import compact_dict, safe_isoformat, safe_attr


def serialize_model(m):
    if not m:
        return None
    return compact_dict({
        "name": m.name,
        "slug": m.slug,
    })


def _normalize_authors(raw_authors):

    def slugify(text):
        if not text:
            return ""
        return re.sub(r'[-\s]+', '-', re.sub(r'[^\w\s-]', '', text.lower())).strip('-')
        
    if not raw_authors:
        return []
    if isinstance(raw_authors, str):
        raw_authors = [raw_authors]
    
    normalized = []
    for a in raw_authors:
        if isinstance(a, str):
            normalized.append({"name": a, "slug": slugify(a)})
        elif isinstance(a, dict) and a.get("name"):
            name = a["name"]
            slug = slugify(name)
            url = a.get("link") if a.get("link") else a.get("uri") if a.get("uri") else None
            normalized.append({"name": name, "slug": slug, "url": url})
    return normalized

def _serialize_authors(authors):
    if not authors:
        return []
    return [
        compact_dict({
            "id": a.id,
            "name": a.name,
            "slug": a.slug,
            "url": a.url,
            "icon_url": a.icon_url,
            "is_agency": a.is_agency,
        }) for a in authors
    ]

def _serialize_sources(sources):
    if not sources:
        return []
    result = []
    for s in sources:
        if s and s.source:
            result.append(compact_dict({
                "name": s.source.name,
                "slug": s.source.slug,
                "url": s.url,
                "published_at": safe_isoformat(s, "published_at"),
                "logo_url": s.source.logo_url if hasattr(s.source, "logo_url") else None,
                "authority_score": s.source.authority_score or 0,
            }))
    return result

def serialize_target(obj, session=None):
    """
    Serializes a polymorphic target object (Article, Video, Post, or Product).
    Ensures all type-specific fields are present for a premium UI.
    """
    if not obj:
        return None

    type_name = obj.__class__.__name__.lower()

    data = {
        "id": obj.id,
        "type": type_name,
    }

    match type_name:
        case "article":
            rel = obj.primary_source if hasattr(obj, "primary_source") else None
            if not rel and obj.article_sources:
                rel = obj.article_sources[0]

            primary_source = None
            if rel and rel.source:
                primary_source = compact_dict({
                    "name": rel.source.name,
                    "slug": rel.source.slug,
                    "url": rel.url,
                    "published_at": safe_isoformat(rel, "published_at"),
                    "logo_url": rel.source.logo_url if hasattr(rel.source, "logo_url") else None,
                    "authority_score": rel.source.authority_score or 0
                })

            serialized_authors = _serialize_authors(obj.authors) if hasattr(obj, "authors") else []
            data.update({
                "title": obj.title,
                "preview_text": obj.preview_text,
                "url": obj.url,
                "image_url": obj.image_url or obj.thumbnail_url if hasattr(obj, "thumbnail_url") else obj.image_url,
                "source_name": obj.source_name,
                "source_url": obj.source_url,
                "read_time_minutes": obj.read_time_minutes,
                "is_content_scraped": obj.is_content_scraped,
                "author": serialized_authors[0] if serialized_authors else None,
                "authors": serialized_authors,
                "sources": _serialize_sources(obj.article_sources),
                "content_text": obj.content_text,
                "content_html": obj.content_html,
                "summary": obj.summary,
                "body": obj.body,
                "description": obj.description,
                "word_count": obj.word_count,
                "sentiment_score": obj.sentiment_score,
                "event": compact_dict({
                    "title": obj.event.title,
                    "external_uri": obj.event.external_uri,
                    "event_date": safe_isoformat(obj.event, "event_date")
                }) if hasattr(obj, "event") and obj.event else None,
                "primary_source": primary_source,
            })

        case "video":
            data.update({
                "title": obj.title,
                "preview_text": obj.description[:200] if obj.description else None,
                "url": obj.url if hasattr(obj, "url") else None,
                "image_url": obj.thumbnail_url,
                "platform": obj.platform,
                "external_id": obj.external_id,
                "channel_name": obj.channel_name,
                "description": obj.description,
                "thumbnail_url": obj.thumbnail_url,
                "duration_seconds": obj.duration_seconds,
            })

        case "post":
            data.update({
                "title": obj.title,
                "preview_text": obj.body[:200] if obj.body else None,
                "url": obj.url if hasattr(obj, "url") else None,
                "image_url": obj.image_url if hasattr(obj, "image_url") else None,
                "platform": obj.platform,
                "external_id": obj.external_id,
                "author": obj.author,
                "subreddit": obj.subreddit,
                "upvotes": obj.upvotes,
                "body": obj.body,
            })

        case "product":
            from app.domains.product.serializers import serialize_item
            
            item_data = serialize_item(obj)
            if item_data:
                data.update(item_data)
                data["title"] = item_data.get("name")
                data["brand_name"] = item_data.get("brand", {}).get("name") if item_data.get("brand") else None
                data["category_name"] = item_data.get("category", {}).get("name") if item_data.get("category") else None
                data["image_url"] = item_data.get("image_url")

    return compact_dict(data)
