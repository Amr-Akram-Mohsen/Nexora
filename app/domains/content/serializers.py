from typing import Optional, Dict, Any
from app.domains.serializers import serialize_model, serialize_target
from slugify import slugify
from app.domains.serialization_utils import compact_dict, safe_isoformat, safe_attr

def _serialize_content_base(content_obj, target_obj=None, session=None, include_linked_items=False, active_filters=None):
    if not content_obj:
        return None
    top_content_entities = sorted(content_obj.content_entities or [], key=lambda ce: ce.relevance_score or 0.0, reverse=True)[:7]
    data = {'id': content_obj.id, 'slug': f'{content_obj.id}-{slugify(content_obj.title)}', 'object_type': content_obj.object_type, 'type': content_obj.object_type, 'section_id': content_obj.section_id, 'category_id': content_obj.category_id, 'published_at': content_obj.published_at.isoformat(), 'is_published': content_obj.is_published, 'is_active': content_obj.is_active, 'view_count': content_obj.view_count, 'comment_count': content_obj.comment_count, 'category': serialize_model(content_obj.category) if content_obj.category and content_obj.category.slug != 'uncategorized' else None, 'section': serialize_model(content_obj.section), 'source': serialize_model(content_obj.source), 'target': serialize_target(target_obj, session) if target_obj else None, 'linked_items': content_obj.linked_products if include_linked_items else None, 'entities': [serialize_model(e.entity) for e in top_content_entities if e.entity], 'locations': [serialize_model(loc) for loc in content_obj.locations or []], 'topics': [serialize_model(e.entity) for e in top_content_entities if e.entity and e.entity.entity_type in ('topic', 'tag', 'concept')], 'brands': [serialize_model(e.entity) for e in top_content_entities if e.entity and e.entity.entity_type in ('brand', 'organization')]}
    display_preview = content_obj.preview_text
    reading_time = None
    event = None
    authors = []
    authority = content_obj.source.authority_score if content_obj.source else 0
    if target_obj:
        match content_obj.object_type:
            case 'article':
                display_preview = display_preview or target_obj.summary or (target_obj.content_text[:200] + '...' if target_obj.content_text and len(target_obj.content_text) > 200 else target_obj.content_text)
                if target_obj.event:
                    event = {'external_uri': target_obj.event.external_uri, 'title': target_obj.event.title, 'summary': target_obj.event.summary, 'event_date': target_obj.event.event_date.isoformat() if target_obj.event.event_date else None, 'image_url': target_obj.event.image_url, 'event_type': target_obj.event.event_type}
                if target_obj.word_count:
                    reading_time = max(1, target_obj.word_count // 200)
                if not authority:
                    if target_obj.primary_source and target_obj.primary_source.source:
                        authority = target_obj.primary_source.source.authority_score or 0
                if hasattr(target_obj, 'authors') and target_obj.authors:
                    authors = [{'name': author.name, 'slug': author.slug, 'url': author.url} for author in target_obj.authors]
            case 'video':
                display_preview = display_preview or target_obj.description
            case 'post':
                display_preview = display_preview or target_obj.body
    if not display_preview:
        display_preview = ''
    source_tier = 'verified' if authority >= 80 else 'trusted' if authority >= 60 else 'standard' if authority >= 40 else 'unverified'
    is_verified_source = source_tier == 'verified'
    data['display_preview'] = display_preview
    data['reading_time'] = reading_time
    data['is_verified_source'] = is_verified_source
    data['source_tier'] = source_tier
    data['authors'] = authors
    data['event'] = event
    return (compact_dict(data), top_content_entities)

def serialize_content_card(content_obj, target_obj=None, session=None, include_linked_items=False, active_filters=None):
    if not content_obj:
        return None
    data, _ = _serialize_content_base(content_obj, target_obj, session, include_linked_items, active_filters)
    return data

def serialize_content_detail(content_obj, target_obj=None, session=None, include_linked_items=False, active_filters=None):
    if not content_obj:
        return None
    data, top_content_entities = _serialize_content_base(content_obj, target_obj, session, include_linked_items, active_filters)
    ENTITY_TYPE_LABELS = {'person': 'People', 'organization': 'Organizations', 'brand': 'Brands', 'location': 'Places', 'concept': 'Topics', 'tag': 'Tags', 'topic': 'Topics', 'wiki_category': 'Topics'}
    grouped_entities = {}
    for ce in top_content_entities:
        if ce.entity:
            etype = ce.entity.entity_type
            label = ENTITY_TYPE_LABELS.get(etype, etype.replace('_', ' ').title())
            grouped_entities.setdefault(label, []).append(serialize_model(ce.entity))
    media_images = getattr(target_obj, 'images', []) if target_obj else []
    media_videos = getattr(target_obj, 'videos', []) if target_obj else []
    video_comments = []
    if target_obj and content_obj.object_type == 'video' and target_obj.video_comments:
        for c in target_obj.video_comments:
            video_comments.append({'author': {'name': c.author_name, 'url': f'https://youtube.com/{c.author_name}'}, 'text': c.text, 'likes': c.like_count, 'replies': c.reply_count, 'published_at': c.published_at.isoformat() if c.published_at else None})
    data['grouped_entities'] = grouped_entities
    data['media_images'] = media_images
    data['media_videos'] = media_videos
    if video_comments:
        data['video_comments'] = video_comments
    return compact_dict(data)

def serialize_content(content_obj, target_obj=None, session=None, include_linked_items=False, active_filters=None):
    return serialize_content_detail(content_obj, target_obj, session, include_linked_items, active_filters)