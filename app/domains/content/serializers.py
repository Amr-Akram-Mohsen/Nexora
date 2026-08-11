from typing import Optional, Dict, Any
from app.domains.serializers import serialize_model, serialize_target
from slugify import slugify
from app.domains.serialization_utils import compact_dict, safe_isoformat, safe_attr

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
        "published_at": content_obj.published_at.isoformat(),
        "is_published": content_obj.is_published,
        "is_active": content_obj.is_active,
        "view_count": content_obj.view_count,
        "comment_count": content_obj.comment_count,
        "category": serialize_model(content_obj.category)
        if safe_attr(content_obj, "category") and content_obj.category.slug != "uncategorized"
        else None,
        "section": serialize_model(content_obj.section),
        "source": serialize_model(safe_attr(content_obj, "source")),
        "target": serialize_target(target_obj, session) if target_obj else None,
        "linked_items": content_obj.linked_products if include_linked_items else None,
        "entities": [serialize_model(e.entity) for e in top_content_entities if e.entity],
        "locations": [serialize_model(loc) for loc in (content_obj.locations or [])],
        "topics": [serialize_model(e.entity) for e in top_content_entities if e.entity and e.entity.entity_type in ('topic', 'tag', 'concept')],
        "brands": [serialize_model(e.entity) for e in top_content_entities if e.entity and e.entity.entity_type in ('brand', 'organization')]
    }

    display_preview = (
        safe_attr(content_obj, "preview_text") or
        safe_attr(target_obj, "description") or
        safe_attr(target_obj, "summary")
    )
    if not display_preview:
        content_text = safe_attr(target_obj, "content_text")
        if content_text:
            display_preview = content_text[:200] + "..." if len(content_text) > 200 else content_text
    
    if not display_preview:
        display_preview = ""
        
    event = safe_attr(target_obj, "event")
    if event:
        event = {
            "external_uri": safe_attr(event, "external_uri"),
            "title": safe_attr(event, "title"),
            "summary": safe_attr(event, "summary"),
            "event_date": safe_isoformat(event, "event_date"),
            "image_url": safe_attr(event, "image_url"),
            "event_type": safe_attr(event, "event_type")
        }

    reading_time = None
    word_count = safe_attr(target_obj, "word_count", 0)
    if word_count:
        reading_time = max(1, word_count // 200)
        
    authority = safe_attr(safe_attr(content_obj, "source"), "authority_score", 0)
    if not authority:
        ps_rel = safe_attr(target_obj, "primary_source")
        if isinstance(ps_rel, dict):
            authority = ps_rel.get('authority_score', 0) or 0
        else:
            authority = safe_attr(safe_attr(ps_rel, "source"), "authority_score", 0)

    source_tier = (
        "verified"   if authority >= 80 else
        "trusted"    if authority >= 60 else
        "standard"   if authority >= 40 else
        "unverified"
    )
    is_verified_source = (source_tier == "verified")
        
    article_authors = safe_attr(target_obj, "article_authors", [])
    authors = [{"name": aa.author.name, "slug": aa.author.slug} for aa in article_authors if aa.author]

    data["display_preview"] = display_preview
    data["reading_time"] = reading_time
    data["is_verified_source"] = is_verified_source
    data["source_tier"] = source_tier
    data["authors"] = authors
    data["event"] = event
    
    return compact_dict(data), top_content_entities

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
            
    media_images = safe_attr(target_obj, "images", [])
    media_videos = safe_attr(target_obj, "videos", [])

    video_comments = []
    if content_obj.object_type == "video":
        target_comments = safe_attr(target_obj, "video_comments", [])
        for c in target_comments:
            video_comments.append({
                "author": {"name": c.author_name, "url": f"https://youtube.com/{c.author_name}"},
                "text": c.text,
                "likes": c.like_count,
                "replies": c.reply_count,
                "published_at": safe_isoformat(c, "published_at")
            })

    data["grouped_entities"] = grouped_entities
    data["media_images"] = media_images
    data["media_videos"] = media_videos
    if video_comments:
        data["video_comments"] = video_comments
        
    return compact_dict(data)

# Keep serialize_content as an alias to serialize_content_detail to prevent breaking other apps temporarily
def serialize_content(content_obj, target_obj=None, session=None, include_linked_items=False, active_filters=None):
    return serialize_content_detail(content_obj, target_obj, session, include_linked_items, active_filters)
