from typing import Optional, Dict, Any
from app.domains.content.service.editorial import assess_video_description, assess_article_extraction
from app.domains.content.service.normalization import calculate_content_health_score
def _serialize_inspect_target(target, object_type) -> Dict[str, Any]:
    if not target:
        return {}
    if object_type == 'video':
        description = getattr(target, 'description', None)
        comments_data = []
        if hasattr(target, 'video_comments'):
            for c in target.video_comments:
                comments_data.append({'id': c.id, 'author': c.author_name, 'text': c.text, 'likes': c.like_count, 'published_at': c.published_at.isoformat() if c.published_at else None})
        return {'platform': getattr(target, 'platform', None), 'channel_name': getattr(target, 'channel_name', None), 'creator': getattr(target, 'creator', None), 'duration_seconds': getattr(target, 'duration_seconds', None), 'external_id': getattr(target, 'external_id', None), 'description': description, 'description_display_rule': getattr(target, 'description_display_rule', 'review'), 'description_quality': assess_video_description(description), 'video_comments': comments_data}
    elif object_type == 'post':
        return {'platform': getattr(target, 'platform', None), 'author': getattr(target, 'author', None), 'subreddit': getattr(target, 'subreddit', None), 'upvotes': getattr(target, 'upvotes', 0), 'platform_comments_count': getattr(target, 'comments_count', 0)}
    elif object_type == 'article':
        return {'is_content_scraped': getattr(target, 'is_content_scraped', False), 'article_quality_score': getattr(target, 'quality_score', 0), 'last_enrichment_attempt': target.last_enrichment_attempt.isoformat() if getattr(target, 'last_enrichment_attempt', None) else None, 'extraction_assessment': assess_article_extraction(target)}
    return {}
def serialize_content_inspect_dto(content, target) -> Optional[Dict[str, Any]]:
    if not content:
        return None
    sources = []
    if content.object_type == 'article' and target and hasattr(target, 'sorted_source_relations'):
        sources = [s.source.name for s in target.sorted_source_relations if s.source]
    elif content.source:
        sources = [content.source.name]
    status_val = getattr(target, 'status', 'complete') if target else 'complete'
    dto = {'id': content.id, 'title': content.title, 'object_type': content.object_type, 'is_published': content.is_published, 'is_active': content.is_active, 'published_at': content.published_at.strftime('%Y-%m-%d') if content.published_at else None, 'ingested_at': content.ingested_at.isoformat() if content.ingested_at else None, 'ingestion_origin': content.ingestion_origin, 'section': {'slug': content.section.slug, 'name': content.section.name} if content.section else None, 'category': {'slug': content.category.slug, 'name': content.category.name} if content.category else None, 'source': {'name': content.source.name} if content.source else None, 'intent': content.intent.name if content.intent else None, 'gender': content.gender.name if content.gender else None, 'price_tier': content.price_tier.name if content.price_tier else None, 'brands': [ce.entity.name for ce in content.content_entities if ce.entity.entity_type == 'brand'], 'topics': [ce.entity.name for ce in content.content_entities if ce.entity.entity_type in ('topic', 'tag', 'concept')], 'attributes': [a.name for a in content.attributes], 'linked_items': [{'id': i.id, 'name': i.name} for i in content.linked_products], 'sources': sources, 'enrichment_status': status_val, 'view_count': content.view_count, 'like_count': content.like_count, 'dislike_count': content.dislike_count, 'comment_count': content.comment_count, 'share_count': content.share_count, 'save_count': content.save_count, 'score': content.score, 'review_score': content.review_score, 'comments': [{'user_name': c.user.name if getattr(c, 'user', None) else f'User #{c.user_id}', 'content': c.content, 'created_at': c.created_at.isoformat() if c.created_at else None} for c in content.comments]}
    dto.update(_serialize_inspect_target(target, content.object_type))
    return dto
def serialize_content_row(c, target, duplicate_titles: set) -> dict:
    source_name = c.source.name if c.source else 'Unknown'
    source_slug = c.source.slug if c.source else 'unknown'
    status_val = 'complete'
    canonical_url = None
    if c.object_type == 'article' and target:
        status_val = target.status
        canonical_url = target.canonical_url
        sources = [s.source.name for s in target.article_sources if s.source]
    else:
        if target:
            canonical_url = target.url
        sources = [c.source.name] if c.source else []
    duplicate = c.title and c.title in duplicate_titles
    score = calculate_content_health_score(c, target, duplicate)
    cat_name = c.category.name if c.category else 'None'
    sec_name = c.section.name if c.section else 'None'
    sources_text = ', '.join(sources)
    return {'id': c.id, 'is_published': c.is_published, 'title': c.title or '', 'object_type': c.object_type, 'category': cat_name, 'section': sec_name, 'has_topics': any((ce.entity.entity_type in ('topic', 'tag', 'concept') for ce in c.content_entities)), 'has_brands': any((ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand' for ce in c.content_entities)), 'has_source': bool(c.source_id), 'is_duplicate': bool(duplicate), 'enrichment_status': status_val, 'health_score': score, 'engagement': {'views': c.view_count, 'likes': c.like_count, 'comments': c.comment_count, 'shares': c.share_count, 'saves': c.save_count}, 'published_at': c.published_at.isoformat() if c.published_at else None, 'sources_text': sources_text, 'ingestion_origin': c.ingestion_origin}