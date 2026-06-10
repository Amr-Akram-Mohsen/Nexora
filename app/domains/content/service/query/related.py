"""
Scored related content recommendations.

Uses the recommendation domain's scoring engine to return the most
taxonomically and contextually relevant content for a given piece of content.

Unlike the old implementation this is NOT section-locked — section match is
a soft scoring signal (+0.5) rather than a hard filter, so cross-section
content can surface when it is genuinely more relevant.
"""
from ...models import Content
from sqlalchemy import case, func, literal_column, cast


def get_related_contents(content_id, limit=6, session=None):
    """
    Return top-N content items most relevant to ``content_id``.

    Scoring signals applied at the SQL aggregation level:
      - Topic overlap   : +3.0 per shared topic
      - Brand overlap   : +2.0 for any shared brand (capped via MAX)
      - Category match  : +1.5 on a match
      - Section match   : +0.5 (soft — cross-section content can still surface)
      - Recency         : up to +0.8 via 1 / (1 + age_days / 30) approximation
      - Popularity      : +log(1 + view_count) × 0.4

    Content with a combined score of 0 is excluded.

    Args:
        session:    DB session (defaults to ``db.session``).
        content_id: ID of the reference content item.
        limit:      Maximum number of results.

    Returns:
        List of serialized content dicts.
    """
    from app.domains.taxonomy.models import Topic, Brand
    from sqlalchemy import Float
    from .utils import build_content_stmt, build_ranked_content_stmt, fetch_serialized_contents

    if session is None:
        from app.core.extensions import db
        session = db.session

    # --- Load reference content ---
    ref_stmt = (
        build_content_stmt(active_only=False, published_only=False, eager_load="default")
        .where(Content.id == content_id)
    )
    reference = session.execute(ref_stmt).scalars().first()
    if not reference:
        return []

    topic_ids = [t.id for t in reference.topics]
    brand_ids = [b.id for b in reference.brands]
    category_id = reference.category_id
    section_id = reference.section_id

    # --- Build scoring expressions ---

    # Topic: +3 per shared topic
    if topic_ids:
        topic_score = case((Topic.id.in_(topic_ids), 3.0), else_=0.0)
    else:
        topic_score = literal_column("0.0")

    # Brand: +2 if any brand matches (MAX to avoid per-row double-counting)
    if brand_ids:
        brand_score = case((Brand.id.in_(brand_ids), 2.0), else_=0.0)
    else:
        brand_score = literal_column("0.0")

    # Category: +1.5 for exact match
    category_score = case((Content.category_id == category_id, 1.5), else_=0.0)

    # Section: +0.5 soft signal (not a hard filter)
    section_score = case((Content.section_id == section_id, 0.5), else_=0.0)

    # Recency: 0.8 / (1 + age_days / 30)  — approximated in SQL
    epoch_diff = func.extract("epoch", func.now() - Content.published_at)
    age_days = epoch_diff / 86400.0
    recency_score = cast(0.8 / (1.0 + age_days / 30.0), Float)

    # Popularity: log(1 + view_count) * 0.4
    popularity_score = cast(func.log(1 + Content.view_count) * 0.4, Float)

    relevance_expr = (
        func.sum(topic_score)
        + func.max(brand_score)
        + func.max(category_score)
        + func.max(section_score)
        + func.max(recency_score)
        + func.max(popularity_score)
    )

    # --- Build query ---
    stmt = build_content_stmt(active_only=True, published_only=True, eager_load="default")
    stmt = (
        stmt
        .outerjoin(Content.topics)
        .outerjoin(Content.brands)
        .where(Content.id != content_id)
    )

    stmt = build_ranked_content_stmt(stmt, relevance_expr, "relevance_score")
    stmt = stmt.having(relevance_expr > 0)

    if limit:
        stmt = stmt.limit(limit)

    return fetch_serialized_contents(stmt, session)
