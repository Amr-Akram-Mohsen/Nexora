"""
Recommendation Scoring Engine
==============================
Pure Python, no DB calls. Operates on model instances or serialized dicts.

Usage example::

    from app.domains.recommendation.ranking import ContentScoreWeights, score_content_relevance

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
    from app.domains.item.models import Item


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
    Weights used when scoring items against a reference content object.
    """
    brand_match: float = 3.0
    category_match: float = 2.0
    direct_link: float = 5.0    # item is explicitly linked via content_items table
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
    ref_topic_ids: set[int] = {t.id for t in (reference.topics or [])}
    ref_brand_ids: set[int] = {b.id for b in (reference.brands or [])}

    candidate_topic_ids: set[int] = {t.id for t in (candidate.topics or [])}
    candidate_brand_ids: set[int] = {b.id for b in (candidate.brands or [])}

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
# Content → Item scoring
# ---------------------------------------------------------------------------

def score_item_relevance(
    item: "Item",
    reference_content: "Content",
    weights: ItemScoreWeights | None = None,
    directly_linked_ids: set[int] | None = None,
) -> float:
    """
    Score how relevant an ``item`` is to a reference ``content`` object.

    Signals:
      - Direct link via content_items association table
      - Brand match between item.brand_id and content's brand IDs
      - Category match between item.category_id and content's category_id

    Args:
        item:                Product to score.
        reference_content:   Content to compare against.
        weights:             Weight configuration.
        directly_linked_ids: Set of item IDs already linked via content_items
                             (avoids re-loading the relationship inside this fn).

    Returns:
        Float relevance score (higher is better).
    """
    if weights is None:
        weights = ItemScoreWeights()

    score = 0.0

    # --- Direct association ---
    if directly_linked_ids and item.id in directly_linked_ids:
        score += weights.direct_link

    # --- Brand match ---
    ref_brand_ids: set[int] = {b.id for b in (reference_content.brands or [])}
    if item.brand_id and item.brand_id in ref_brand_ids:
        score += weights.brand_match

    # --- Category match ---
    if item.category_id and item.category_id == reference_content.category_id:
        score += weights.category_match

    # --- Popularity ---
    score += weights.popularity * _log_popularity(item.view_count)

    return score
