from __future__ import annotations
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.domains.content.models import Content
    from app.domains.product.models import Product

@dataclass
class ContentScoreWeights:
    topic_match: float = 3.0
    brand_match: float = 2.0
    category_match: float = 1.5
    section_match: float = 0.5
    recency: float = 0.8
    popularity: float = 0.4
    trending: float = 0.3

@dataclass
class ItemScoreWeights:
    brand_match: float = 3.0
    category_match: float = 2.0
    direct_link: float = 5.0
    popularity: float = 0.4

def _recency_decay(published_at: datetime | None, half_life_days: float=30.0) -> float:
    if not published_at:
        return 0.0
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age_days = max((datetime.now(timezone.utc) - published_at).days, 0)
    return math.exp(-math.log(2) * age_days / half_life_days)

def _log_popularity(view_count: int | None) -> float:
    return math.log1p(max(view_count or 0, 0))

def score_content_relevance(candidate: 'Content', reference: 'Content', weights: ContentScoreWeights | None=None) -> float:
    if weights is None:
        weights = ContentScoreWeights()
    score = 0.0
    ref_topic_ids: set[int] = {ce.entity.id for ce in reference.content_entities or [] if ce.entity.entity_type in ('topic', 'tag', 'concept')}
    ref_brand_ids: set[int] = {ce.entity.id for ce in reference.content_entities or [] if ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand'}
    candidate_topic_ids: set[int] = {ce.entity.id for ce in candidate.content_entities or [] if ce.entity.entity_type in ('topic', 'tag', 'concept')}
    candidate_brand_ids: set[int] = {ce.entity.id for ce in candidate.content_entities or [] if ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand'}
    matching_topics = ref_topic_ids & candidate_topic_ids
    score += len(matching_topics) * weights.topic_match
    if ref_brand_ids & candidate_brand_ids:
        score += weights.brand_match
    if reference.category_id and reference.category_id == candidate.category_id:
        score += weights.category_match
    if reference.section_id and reference.section_id == candidate.section_id:
        score += weights.section_match
    score += weights.recency * _recency_decay(candidate.published_at)
    score += weights.popularity * _log_popularity(candidate.view_count)
    return score

def score_item_relevance(product: 'Product', reference_content: 'Content', weights: ItemScoreWeights | None=None, directly_linked_ids: set[int] | None=None) -> float:
    if weights is None:
        weights = ItemScoreWeights()
    score = 0.0
    if directly_linked_ids and product.id in directly_linked_ids:
        score += weights.direct_link
    ref_brand_ids: set[int] = {ce.entity.id for ce in reference_content.content_entities or [] if ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand'}
    if product.brand_id and product.brand_id in ref_brand_ids:
        score += weights.brand_match
    if product.category_id and product.category_id == reference_content.category_id:
        score += weights.category_match
    score += weights.popularity * _log_popularity(product.view_count)
    return score

@dataclass
class ContentItemLinkWeights:
    category_match: float = 3.0
    parent_category_match: float = 1.5
    brand_match: float = 4.0
    brand_name_in_title: float = 2.0
    topic_match: float = 1.5
    text_overlap: float = 2.5

def score_content_item_link(content: 'Content', product: 'Product', weights: ContentItemLinkWeights | None=None) -> float:
    if weights is None:
        weights = ContentItemLinkWeights()
    score = 0.0
    if content.category_id and product.category_id:
        if content.category_id == product.category_id:
            score += weights.category_match
        elif content.category and product.category:
            if content.category.parent_id and content.category.parent_id == product.category.parent_id:
                score += weights.parent_category_match
            elif content.category.parent_id == product.category_id or product.category.parent_id == content.category_id:
                score += weights.parent_category_match
    content_brand_ids = {ce.entity.id for ce in content.content_entities or [] if ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand'}
    if product.brand_id and product.brand_id in content_brand_ids:
        score += weights.brand_match
    elif product.brand and product.brand.name:
        brand_name_lower = product.brand.name.lower()
        content_title_lower = (content.title or '').lower()
        if brand_name_lower in content_title_lower:
            score += weights.brand_name_in_title
    item_name_lower = (product.name or '').lower()
    item_desc_lower = (product.description or '').lower()
    for topic in (ce.entity for ce in content.content_entities or [] if ce.entity.entity_type in ('topic', 'tag', 'concept')):
        if topic.name:
            topic_name_lower = topic.name.lower()
            if topic_name_lower in item_name_lower or topic_name_lower in item_desc_lower:
                score += weights.topic_match
    if product.name:
        content_title_lower = (content.title or '').lower()
        if item_name_lower in content_title_lower:
            score += weights.text_overlap
        else:
            stop_words = {'with', 'and', 'the', 'for', 'pro', 'max', 'ultra', 'plus', 'new'}
            item_tokens = [w for w in item_name_lower.split() if len(w) > 2 and w not in stop_words]
            if item_tokens:
                title_words = set(content_title_lower.split())
                overlap = len(title_words.intersection(item_tokens))
                if overlap >= 2:
                    score += weights.text_overlap * (overlap / len(item_tokens))
    return score