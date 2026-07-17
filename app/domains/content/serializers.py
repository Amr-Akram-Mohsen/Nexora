from typing import Optional, Dict, Any
from app.domains.serializers import serialize_model, serialize_target
from app.domains.content.service.editorial import assess_video_description, assess_article_extraction
def _serialize_inspect_target(target, object_type) -> Dict[str, Any]:
    if not target:
        return {}
    
    if object_type == "video":
        description = getattr(target, "description", None)
        return {
            "platform": getattr(target, "platform", None),
            "channel_name": getattr(target, "channel_name", None),
            "creator": getattr(target, "creator", None),
            "duration_seconds": getattr(target, "duration_seconds", None),
            "external_id": getattr(target, "external_id", None),
            "description": description,
            "description_display_rule": getattr(target, "description_display_rule", "review"),
            "description_quality": assess_video_description(description)
        }
    elif object_type == "post":
        return {
            "platform": getattr(target, "platform", None),
            "author": getattr(target, "author", None),
            "subreddit": getattr(target, "subreddit", None),
            "upvotes": getattr(target, "upvotes", 0),
            "platform_comments_count": getattr(target, "comments_count", 0)
        }
    elif object_type == "article":
        return {
            "is_content_scraped": getattr(target, "is_content_scraped", False),
            "article_quality_score": getattr(target, "quality_score", 0),
            "last_enrichment_attempt": target.last_enrichment_attempt.isoformat() if getattr(target, "last_enrichment_attempt", None) else None,
            "extraction_assessment": assess_article_extraction(target)
        }
    return {}

def serialize_content_inspect_dto(content, target) -> Optional[Dict[str, Any]]:
    """
    Serializes a Content ORM model and its polymorphic target into a flat, 
    presentation-agnostic DTO dictionary.
    """
    if not content:
        return None

    sources = []
    if content.object_type == "article" and target and hasattr(target, "sorted_source_relations"):
        sources = [s.source.name for s in target.sorted_source_relations if s.source]
    elif content.source:
        sources = [content.source.name]

    status_val = getattr(target, "status", "complete") if target else "complete"

    dto = {
        "id": content.id,
        "title": content.title,
        "object_type": content.object_type,
        "is_published": content.is_published,
        "is_active": content.is_active,
        "published_at": content.published_at.strftime("%Y-%m-%d") if content.published_at else None,
        "ingested_at": content.ingested_at.isoformat() if content.ingested_at else None,
        "ingestion_origin": content.ingestion_origin,
        
        "section": {"slug": content.section.slug, "name": content.section.name} if content.section else None,
        "category": {"slug": content.category.slug, "name": content.category.name} if content.category else None,
        "source": {"name": content.source.name} if content.source else None,
        
        "intent": content.intent.name if content.intent else None,
        "gender": content.gender.name if content.gender else None,
        "price_tier": content.price_tier.name if content.price_tier else None,
        
        "brands": [ce.entity.name for ce in content.content_entities if ce.entity.entity_type == 'brand'],
        "topics": [ce.entity.name for ce in content.content_entities if ce.entity.entity_type in ('topic', 'tag', 'concept')],
        "attributes": [a.name for a in content.attributes],
        "linked_items": [{"id": i.id, "name": i.name} for i in content.linked_products],
        "sources": sources,
        
        "enrichment_status": status_val,
        "view_count": content.view_count,
        "like_count": content.like_count,
        "dislike_count": content.dislike_count,
        "comment_count": content.comment_count,
        "share_count": content.share_count,
        "save_count": content.save_count,
        "score": content.score,
        "review_score": content.review_score,
        
        "comments": [
            {
                "user_name": c.user.name if getattr(c, "user", None) else f"User #{c.user_id}",
                "content": c.content,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in content.comments
        ]
    }

    dto.update(_serialize_inspect_target(target, content.object_type))

    return dto

def _calculate_content_health_score(c, target, duplicate):
    score = 0
    if c.title: score += 10
    if c.preview_text or getattr(target, 'description', None) or getattr(target, 'preview_text', None): score += 10
    if c.category and c.category.slug != 'uncategorized': score += 10
    has_topics = any(ce.entity.entity_type in ('topic', 'tag', 'concept') for ce in c.content_entities)
    has_brands = any(ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand' for ce in c.content_entities)
    if has_topics: score += 15
    if has_brands: score += 15
    if c.source_id: score += 10
    if not duplicate: score += 5
    
    if c.object_type == "article" and target:
        if getattr(target, 'is_content_scraped', False): score += 10
        if getattr(target, 'status', '') == 'complete': score += 10
        if getattr(target, 'quality_score', 0) > 0: score += 5
    elif c.object_type in ("video", "post"):
        score += 25
        
    return min(score, 100)

def serialize_content_row(c, target, duplicate_titles: set) -> dict:
    """
    Serialize a single Content row for the admin listing.

    Args:
        c: The Content ORM instance.
        target: The polymorphic target (Article / Video / Post) or None.
        duplicate_titles: Set of titles known to be duplicated on the current page.

    Returns:
        A dict suitable for JSON serialization.
    """
    source_name  = c.source.name if c.source else "Unknown"
    source_slug  = c.source.slug if c.source else "unknown"
    status_val   = "complete"
    canonical_url = None

    if c.object_type == "article" and target:
        status_val    = target.status
        canonical_url = target.canonical_url
        sources = [s.source.name for s in target.article_sources if s.source]
    else:
        if target:
            canonical_url = target.url
        sources = [c.source.name] if c.source else []

    # Quality flags
    duplicate = c.title and c.title in duplicate_titles
    
    score = _calculate_content_health_score(c, target, duplicate)

    cat_name = c.category.name if c.category else "None"
    sec_name = c.section.name if c.section else "None"
    sources_text = ", ".join(sources)

    return {
        "id": c.id,
        "is_published": c.is_published,
        "title": c.title or "",
        "object_type": c.object_type,
        "category": cat_name,
        "section": sec_name,
        "has_topics": any(ce.entity.entity_type in ('topic', 'tag', 'concept') for ce in c.content_entities),
        "has_brands": any(ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand' for ce in c.content_entities),
        "has_source": bool(c.source_id),
        "is_duplicate": bool(duplicate),
        "enrichment_status": status_val,
        "health_score": score,
        "engagement": {
            "views": c.view_count, 
            "likes": c.like_count, 
            "comments": c.comment_count, 
            "shares": c.share_count, 
            "saves": c.save_count
        },
        "published_at": c.published_at.isoformat() if c.published_at else None,
        "sources_text": sources_text,
        "ingestion_origin": c.ingestion_origin,
    }

def serialize_content(content_obj, target_obj=None, session=None, include_linked_items=False, active_filters=None):
    """
    Serializes a Content model into a predictable dictionary.
    """
    if not content_obj:
        return None

    data = {
        "id": content_obj.id,
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
        "entities": [serialize_model(e.entity) for e in (content_obj.content_entities or []) if e.entity],
        "locations": [serialize_model(loc) for loc in (content_obj.locations or [])],
    }

    # -- UI Presentation Computed Fields --
    display_preview = ""
    if getattr(content_obj, "preview_text", None):
        display_preview = content_obj.preview_text
    elif target_obj and getattr(target_obj, "description", None):
        display_preview = target_obj.description
    elif target_obj and getattr(target_obj, "summary", None):
        display_preview = target_obj.summary
    elif target_obj and getattr(target_obj, "content_text", None):
        display_preview = target_obj.content_text[:200] + "..." if len(target_obj.content_text) > 200 else target_obj.content_text
        
    display_badges = []
    if content_obj.category and content_obj.category.slug != "uncategorized":
        display_badges.append({"text": content_obj.category.name, "class": "badge--category", "variant": "secondary", "icon": None})
        
    locations = content_obj.locations or []
    event = getattr(target_obj, "event", None) if target_obj else None
    
    if locations:
        display_loc = locations[0]
        if active_filters:
            req_locs = []
            if "location" in active_filters:
                r_loc = active_filters["location"]
                req_locs.extend(r_loc if isinstance(r_loc, list) else [r_loc])
            if "entity" in active_filters:
                r_ent = active_filters["entity"]
                req_locs.extend(r_ent if isinstance(r_ent, list) else [r_ent])
                
            loc_slugs = [s.lower() for s in req_locs if s]
            for loc in locations:
                if loc.slug.lower() in loc_slugs:
                    display_loc = loc
                    break
        display_badges.append({"text": display_loc.name, "class": "badge--location", "variant": "info", "icon": "fas fa-map-marker-alt"})
    elif event:
        display_badges.append({"text": event.title, "class": "badge--event", "variant": "primary", "icon": "fas fa-map-marker-alt"})
    else:
        entities = [e.entity for e in (content_obj.content_entities or []) if e.entity]
        if entities:
            # Helper to find an active entity by type
            def find_active_entity(valid_types):
                # Try to find one that matches the active filter first
                if active_filters and "entity" in active_filters:
                    req_ents = active_filters["entity"]
                    if isinstance(req_ents, str):
                        req_ents = [req_ents]
                    ent_slugs = [s.lower() for s in req_ents if s]
                    for e in entities:
                        if e.entity_type in valid_types and e.slug.lower() in ent_slugs:
                            return e
                # Fallback to the first one available
                return next((e for e in entities if e.entity_type in valid_types), None)

            brand = find_active_entity(("brand", "organization"))
            topic = find_active_entity(("topic", "tag", "concept", "person"))
            
            if brand:
                display_badges.append({"text": brand.name, "class": "badge--brand", "variant": "secondary", "icon": "fas fa-tag"})
            elif topic:
                display_badges.append({"text": topic.name, "class": "badge--topic", "variant": "secondary", "icon": "fas fa-hashtag"})

    grouped_entities = {}
    for ce in (content_obj.content_entities or []):
        if ce.entity:
            etype = ce.entity.entity_type
            grouped_entities.setdefault(etype, []).append(serialize_model(ce.entity))
            
    # Phase 2 UI Computed Fields
    reading_time = None
    if target_obj and getattr(target_obj, "word_count", 0):
        reading_time = max(1, target_obj.word_count // 200)
        
    is_verified_source = False
    if content_obj.source and getattr(content_obj.source, "authority_score", 0) >= 75:
        is_verified_source = True
        
    authors = []
    if target_obj and hasattr(target_obj, "article_authors"):
        # Relational authors (from article_author mapping)
        authors = [{"name": aa.author.name, "slug": aa.author.slug} for aa in target_obj.article_authors if aa.author]
    elif target_obj and getattr(target_obj, "authors", None):
        # Fallback to string array or raw dicts from API
        raw_authors = target_obj.authors
        if isinstance(raw_authors, list):
            for a in raw_authors:
                if isinstance(a, str):
                    authors.append({"name": a})
                elif isinstance(a, dict):
                    authors.append({
                        "name": a.get("name") or "Unknown Author",
                        "url": a.get("url", a.get("uri", "")),
                        "email": a.get("email", "")
                    })

    event = None
    if target_obj and getattr(target_obj, "event", None):
        e = target_obj.event
        event = {
            "external_uri": e.external_uri,
            "title": e.title,
            "summary": e.summary,
            "event_date": e.event_date.isoformat() if e.event_date else None,
            "image_url": e.image_url,
            "event_type": e.event_type
        }

    data["display_preview"] = display_preview
    data["display_badges"] = display_badges
    data["grouped_entities"] = grouped_entities
    data["reading_time"] = reading_time
    data["is_verified_source"] = is_verified_source
    data["authors"] = authors
    data["event"] = event

    return data
