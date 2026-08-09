"""
Recommendation Scoring Engine
==============================
Pure Python, no DB calls. Operates on model instances or serialized dicts.

Usage example::

    from app.domains.recommendation.service.ranking import ContentScoreWeights, score_content_relevance

    weights = ContentScoreWeights()  # default weights
    score = score_content_relevance(candidate, reference, weights)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domains.content.models import Content
    from app.domains.product.models import Product


# ---------------------------------------------------------------------------
# Weight configuration
# ---------------------------------------------------------------------------

@dataclass
class ContentScoreWeights:
    """
    Configurable weights for the multi-signal content relevance scorer.

    Each weight is added to the final float score when the corresponding
    signal fires. Weights should be positive; they can be scaled relative
    to each other (e.g. brand_match > category_match).

    Attributes:
        topic_match:    Weight per matching topic.
        brand_match:    Weight for at least one matching brand.
        category_match: Weight for matching category_id.
        section_match:  Weight for matching section_id (soft signal).
        recency:        Maximum contribution from recency decay (0 → 1 scale).
        popularity:     Weight multiplier for log-normalized view_count.
        trending:       Weight multiplier for log-normalized trending score.
    """
    topic_match: float = 3.0
    brand_match: float = 2.0
    category_match: float = 1.5
    section_match: float = 0.5
    recency: float = 0.8
    popularity: float = 0.4
    trending: float = 0.3


@dataclass
class ItemScoreWeights:
    """
    Weights used when scoring products against a reference content object.
    """
    brand_match: float = 3.0
    category_match: float = 2.0
    direct_link: float = 5.0    # product is explicitly linked via content_products table
    popularity: float = 0.4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _recency_decay(published_at: datetime | None, half_life_days: float = 30.0) -> float:
    """
    Exponential time-decay returning a value in [0, 1].

    Score is 1.0 for content published today, 0.5 at ``half_life_days``,
    and approaches 0 for very old content.

    Args:
        published_at:   Publication timestamp (aware or naive UTC).
        half_life_days: Days after which the score halves. Default 30.

    Returns:
        Float in [0.0, 1.0].
    """
    if not published_at:
        return 0.0

    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    age_days = max((datetime.now(timezone.utc) - published_at).days, 0)
    return math.exp(-math.log(2) * age_days / half_life_days)


def _log_popularity(view_count: int | None) -> float:
    """Log-normalized popularity score from a raw view count."""
    return math.log1p(max(view_count or 0, 0))


# ---------------------------------------------------------------------------
# Content ↔ Content scoring
# ---------------------------------------------------------------------------

def score_content_relevance(
    candidate: "Content",
    reference: "Content",
    weights: ContentScoreWeights | None = None,
) -> float:
    """
    Score how relevant ``candidate`` is to ``reference`` content.

    Signals:
      - Topic overlap (per matching topic)
      - Brand overlap (boolean — at least one shared brand)
      - Category match
      - Section match (soft)
      - Recency decay on candidate publication date
      - Popularity (log-normalized view count)

    Args:
        candidate: Content instance to score.
        reference: The source content we are finding recommendations for.
        weights:   Weight configuration; defaults to ``ContentScoreWeights()``.

    Returns:
        Float relevance score (higher is better).
    """
    if weights is None:
        weights = ContentScoreWeights()

    score = 0.0

    # --- Taxonomy signals ---
    ref_topic_ids: set[int] = {ce.entity.id for ce in (reference.content_entities or []) if ce.entity.entity_type in ('topic', 'tag', 'concept')}
    ref_brand_ids: set[int] = {ce.entity.id for ce in (reference.content_entities or []) if ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand'}

    candidate_topic_ids: set[int] = {ce.entity.id for ce in (candidate.content_entities or []) if ce.entity.entity_type in ('topic', 'tag', 'concept')}
    candidate_brand_ids: set[int] = {ce.entity.id for ce in (candidate.content_entities or []) if ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand'}

    matching_topics = ref_topic_ids & candidate_topic_ids
    score += len(matching_topics) * weights.topic_match

    if ref_brand_ids & candidate_brand_ids:
        score += weights.brand_match

    if reference.category_id and reference.category_id == candidate.category_id:
        score += weights.category_match

    if reference.section_id and reference.section_id == candidate.section_id:
        score += weights.section_match

    # --- Freshness ---
    score += weights.recency * _recency_decay(candidate.published_at)

    # --- Popularity ---
    score += weights.popularity * _log_popularity(candidate.view_count)

    return score


# ---------------------------------------------------------------------------
# Content → Product scoring
# ---------------------------------------------------------------------------

def score_item_relevance(
    product: "Product",
    reference_content: "Content",
    weights: ItemScoreWeights | None = None,
    directly_linked_ids: set[int] | None = None,
) -> float:
    """
    Score how relevant an ``product`` is to a reference ``content`` object.

    Signals:
      - Direct link via content_products association table
      - Brand match between product.brand_id and content's brand IDs
      - Category match between product.category_id and content's category_id

    Args:
        product:                Product to score.
        reference_content:   Content to compare against.
        weights:             Weight configuration.
        directly_linked_ids: Set of product IDs already linked via content_products
                             (avoids re-loading the relationship inside this fn).

    Returns:
        Float relevance score (higher is better).
    """
    if weights is None:
        weights = ItemScoreWeights()

    score = 0.0

    # --- Direct association ---
    if directly_linked_ids and product.id in directly_linked_ids:
        score += weights.direct_link

    # --- Brand match ---
    ref_brand_ids: set[int] = {ce.entity.id for ce in (reference_content.content_entities or []) if ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand'}
    if product.brand_id and product.brand_id in ref_brand_ids:
        score += weights.brand_match

    # --- Category match ---
    if product.category_id and product.category_id == reference_content.category_id:
        score += weights.category_match

    # --- Popularity ---
    score += weights.popularity * _log_popularity(product.view_count)

    return score


@dataclass
class ContentItemLinkWeights:
    """
    Configurable weights for the Content ↔ Product periodic matching workflow.
    """
    category_match: float = 3.0
    parent_category_match: float = 1.5
    brand_match: float = 4.0
    brand_name_in_title: float = 2.0
    topic_match: float = 1.5  # per matching topic in product name/description
    text_overlap: float = 2.5  # product name contained in content title


def score_content_item_link(
    content: "Content",
    product: "Product",
    weights: ContentItemLinkWeights | None = None,
) -> float:
    """
    Score the match strength between a Content object and an Product object.

    Signals:
      - Category Match: Same category (category_match)
      - Parent Category Match: Share parent category (parent_category_match)
      - Brand Match: Product brand matches one of Content's brands (brand_match)
      - Brand Name in Title: Product brand name is mentioned in Content title (brand_name_in_title)
      - Topic Match: Content's topic name is mentioned in Product's name/description (topic_match per topic)
      - Text Overlap: Product's name is a substring of the Content's title (text_overlap)
    """
    if weights is None:
        weights = ContentItemLinkWeights()

    score = 0.0

    # 1. Category Match
    if content.category_id and product.category_id:
        if content.category_id == product.category_id:
            score += weights.category_match
        elif content.category and product.category:
            # Check if they share the same parent category
            if content.category.parent_id and content.category.parent_id == product.category.parent_id:
                score += weights.parent_category_match
            # Or if one is parent of the other
            elif content.category.parent_id == product.category_id or product.category.parent_id == content.category_id:
                score += weights.parent_category_match

    # 2. Brand Match
    content_brand_ids = {ce.entity.id for ce in (content.content_entities or []) if ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand'}
    if product.brand_id and product.brand_id in content_brand_ids:
        score += weights.brand_match
    # Soft Brand name match in Content title (if brand ID doesn't match directly)
    elif product.brand and product.brand.name:
        brand_name_lower = product.brand.name.lower()
        content_title_lower = (content.title or "").lower()
        if brand_name_lower in content_title_lower:
            score += weights.brand_name_in_title

    # 3. Topic Match
    item_name_lower = (product.name or "").lower()
    item_desc_lower = (product.description or "").lower()
    for topic in (ce.entity for ce in (content.content_entities or []) if ce.entity.entity_type in ('topic', 'tag', 'concept')):
        if topic.name:
            topic_name_lower = topic.name.lower()
            if topic_name_lower in item_name_lower or topic_name_lower in item_desc_lower:
                score += weights.topic_match

    # 4. Text Overlap / Substring Match
    if product.name:
        content_title_lower = (content.title or "").lower()
        if item_name_lower in content_title_lower:
            score += weights.text_overlap
        else:
            # Check if significant name words are present in title (token match)
            # Filter out short or extremely common words to avoid false positives
            stop_words = {"with", "and", "the", "for", "pro", "max", "ultra", "plus", "new"}
            item_tokens = [w for w in item_name_lower.split() if len(w) > 2 and w not in stop_words]
            if item_tokens:
                title_words = set(content_title_lower.split())
                overlap = len(title_words.intersection(item_tokens))
                if overlap >= 2:
                    score += weights.text_overlap * (overlap / len(item_tokens))

    return score

