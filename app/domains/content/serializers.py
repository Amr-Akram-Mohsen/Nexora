from typing import Optional, Dict, Any
from app.domains.serializers import serialize_model, serialize_target
from slugify import slugify

def _serialize_content_base(content_obj, target_obj=None, session=None, include_linked_items=False, active_filters=None):
    if not content_obj:
        return None

    top_content_entities = sorted(
        content_obj.content_entities or [],
        key=lambda ce: ce.relevance_score or 0.0,
        reverse=True
    )[:7]

    data = {
        "id": content_obj.id,
        "slug": f"{content_obj.id}-{slugify(content_obj.title)}",
        "object_type": content_obj.object_type,
        "type": content_obj.object_type,
        "section_id": content_obj.section_id,
        "category_id": content_obj.category_id,
        "published_at": content_obj.published_at.isoformat() if content_obj.published_at else None,
        "is_published": getattr(content_obj, "is_published", True),
        "is_active": getattr(content_obj, "is_active", True),
        "view_count": getattr(content_obj, "view_count", 0),
        "comment_count": getattr(content_obj, "comment_count", 0),
        "category": serialize_model(content_obj.category)
        if getattr(content_obj, "category", None) and content_obj.category.slug != "uncategorized"
        else None,
        "section": serialize_model(content_obj.section),
        "source": serialize_model(content_obj.source) if getattr(content_obj, "source", None) else None,
        "target": serialize_target(target_obj, session) if target_obj else None,
        "linked_items": content_obj.linked_products if include_linked_items else None,
        "entities": [serialize_model(e.entity) for e in top_content_entities if e.entity],
        "locations": [serialize_model(loc) for loc in (content_obj.locations or [])],
        "topics": [serialize_model(e.entity) for e in top_content_entities if e.entity and e.entity.entity_type in ('topic', 'tag', 'concept')],
        "brands": [serialize_model(e.entity) for e in top_content_entities if e.entity and e.entity.entity_type in ('brand', 'organization')]
    }

    display_preview = ""
    if getattr(content_obj, "preview_text", None):
        display_preview = content_obj.preview_text
    elif target_obj and getattr(target_obj, "description", None):
        display_preview = target_obj.description
    elif target_obj and getattr(target_obj, "summary", None):
        display_preview = target_obj.summary
    elif target_obj and getattr(target_obj, "content_text", None):
        display_preview = target_obj.content_text[:200] + "..." if len(target_obj.content_text) > 200 else target_obj.content_text
        
    event = getattr(target_obj, "event", None) if target_obj else None
    if event:
        event = {
            "external_uri": getattr(event, "external_uri", None),
            "title": getattr(event, "title", None),
            "summary": getattr(event, "summary", None),
            "event_date": event.event_date.isoformat() if getattr(event, "event_date", None) else None,
            "image_url": getattr(event, "image_url", None),
            "event_type": getattr(event, "event_type", None)
        }

    reading_time = None
    if target_obj and getattr(target_obj, "word_count", 0):
        reading_time = max(1, target_obj.word_count // 200)
        
    authority = 0
    if content_obj.source and getattr(content_obj.source, 'authority_score', None) is not None:
        authority = content_obj.source.authority_score or 0
    elif target_obj and getattr(target_obj, 'primary_source', None):
        ps_rel = getattr(target_obj, 'primary_source', None)
        if ps_rel and getattr(ps_rel, 'source', None):
            authority = getattr(ps_rel.source, 'authority_score', 0) or 0
    elif target_obj and isinstance(target_obj, dict) and target_obj.get('primary_source'):
        authority = target_obj['primary_source'].get('authority_score', 0) or 0

    source_tier = (
        "verified"   if authority >= 80 else
        "trusted"    if authority >= 60 else
        "standard"   if authority >= 40 else
        "unverified"
    )
    is_verified_source = (source_tier == "verified")
        
    authors = []
    if target_obj and hasattr(target_obj, "article_authors"):
        authors = [{"name": aa.author.name, "slug": aa.author.slug} for aa in target_obj.article_authors if aa.author]

    data["display_preview"] = display_preview
    data["reading_time"] = reading_time
    data["is_verified_source"] = is_verified_source
    data["source_tier"] = source_tier
    data["authors"] = authors
    data["event"] = event
    
    return data, top_content_entities

def serialize_content_card(content_obj, target_obj=None, session=None, include_linked_items=False, active_filters=None):
    """
    Lightweight serializer for list views, feeds, and carousels.
    """
    if not content_obj:
        return None
        
    data, _ = _serialize_content_base(content_obj, target_obj, session, include_linked_items, active_filters)
    return data

def serialize_content_detail(content_obj, target_obj=None, session=None, include_linked_items=False, active_filters=None):
    """
    Heavyweight serializer for detailed content pages. Includes media and comments.
    """
    if not content_obj:
        return None
        
    data, top_content_entities = _serialize_content_base(content_obj, target_obj, session, include_linked_items, active_filters)
    
    ENTITY_TYPE_LABELS = {
        "person": "People",
        "organization": "Organizations",
        "brand": "Brands",
        "location": "Places",
        "concept": "Topics",
        "tag": "Tags",
        "topic": "Topics",
        "wiki_category": "Topics",
    }
    grouped_entities = {}
    for ce in top_content_entities:
        if ce.entity:
            etype = ce.entity.entity_type
            label = ENTITY_TYPE_LABELS.get(etype, etype.replace('_', ' ').title())
            grouped_entities.setdefault(label, []).append(serialize_model(ce.entity))
            
    media_images = []
    media_videos = []
    if target_obj:
        media_images = getattr(target_obj, "images", []) or []
        media_videos = getattr(target_obj, "videos", []) or []

    video_comments = []
    if content_obj.object_type == "video" and target_obj and hasattr(target_obj, "video_comments"):
        for c in target_obj.video_comments:
            video_comments.append({
                "author": {"name": c.author_name, "url": f"https://youtube.com/{c.author_name}"},
                "text": c.text,
                "likes": c.like_count,
                "replies": c.reply_count,
                "published_at": c.published_at.isoformat() if c.published_at else None
            })

    data["grouped_entities"] = grouped_entities
    data["media_images"] = media_images
    data["media_videos"] = media_videos
    if video_comments:
        data["video_comments"] = video_comments
        
    return data

# Keep serialize_content as an alias to serialize_content_detail to prevent breaking other apps temporarily
def serialize_content(content_obj, target_obj=None, session=None, include_linked_items=False, active_filters=None):
    return serialize_content_detail(content_obj, target_obj, session, include_linked_items, active_filters)
