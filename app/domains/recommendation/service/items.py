"""
Recommendation service — item queries.

Functions surface item recommendations driven by content relationships
(content_items association) and taxonomy overlap.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.extensions import db
from app.domains.item.models import Item


def get_items_for_content(
    content_id: int,
    limit: int = 8,
    session=None,
) -> list[dict]:
    """
    Return items most relevant to a given content piece.

    Strategy (two-phase):
    1. Directly linked items via the ``content_items`` association table
       get a score bonus (+5). These are the highest-confidence matches
       (explicitly curated or matched by the article-item matcher).
    2. Items sharing brand or category with the content's taxonomy fill
       remaining slots.

    Items are returned serialized (same shape as ``serialize_item``).
    """
    from app.domains.content.models import Content
    from app.domains.item.service.utils import build_item_stmt, fetch_items
    from app.domains.item.service.serializers import serialize_item
    from app.domains.recommendation.ranking import (
        ItemScoreWeights,
        score_item_relevance,
    )
    from app.domains.content.service.query.utils import build_content_stmt

    if session is None:
        session = db.session

    # Load reference content with taxonomy
    ref_stmt = (
        build_content_stmt(active_only=False, published_only=False, eager_load="default")
        .where(Content.id == content_id)
    )
    reference = session.execute(ref_stmt).scalars().first()
    if not reference:
        return []

    # 1. Directly linked items
    directly_linked_ids: set[int] = {item.id for item in (reference.linked_items or [])}

    ref_brand_ids: set[int] = {b.id for b in (reference.brands or [])}
    ref_category_id = reference.category_id

    # Candidate pool: linked items + same-category + same-brand items
    from sqlalchemy import or_

    stmt = build_item_stmt(eager_load="card")

    # Include items that match at least one signal
    if directly_linked_ids or ref_brand_ids or ref_category_id:
        conditions = []
        if directly_linked_ids:
            conditions.append(Item.id.in_(list(directly_linked_ids)))
        if ref_brand_ids:
            conditions.append(Item.brand_id.in_(list(ref_brand_ids)))
        if ref_category_id:
            conditions.append(Item.category_id == ref_category_id)
        stmt = stmt.where(or_(*conditions))
    else:
        return []

    # Fetch candidate pool (wider than limit to allow re-ranking)
    stmt = stmt.limit(max(limit * 4, 40))
    candidates = fetch_items(stmt, session)

    if not candidates:
        return []

    # Python-level scoring & sorting (pool is small, avoids complex SQL)
    weights = ItemScoreWeights()
    scored = [
        (item, score_item_relevance(item, reference, weights, directly_linked_ids))
        for item in candidates
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    return [serialize_item(item) for item, _ in scored[:limit]]


def get_trending_items(
    limit: int = 8,
    days: int = 7,
    session=None,
) -> list[dict]:
    """
    Return items ranked by total views + clicks in the past ``days`` days.

    Uses the ``view_count`` and ``click_count`` denormalized counters on
    ``Item`` for efficiency (no join on the views table needed).
    """
    from app.domains.item.service.utils import build_item_stmt, fetch_items
    from app.domains.item.service.serializers import serialize_item

    if session is None:
        session = db.session

    stmt = (
        build_item_stmt(eager_load="card")
        .order_by(
            (Item.view_count + Item.click_count).desc(),
            Item.created_at.desc(),
        )
    )

    if limit:
        stmt = stmt.limit(limit)

    items = fetch_items(stmt, session)
    return [serialize_item(item) for item in items]


def get_popular_items_by_brand(
    brand_id: int,
    limit: int = 6,
    session=None,
) -> list[dict]:
    """
    Return the most popular items for a specific brand, by view count.
    """
    from app.domains.item.service.utils import build_item_stmt, fetch_items
    from app.domains.item.service.serializers import serialize_item

    if session is None:
        session = db.session

    stmt = (
        build_item_stmt(eager_load="card")
        .where(Item.brand_id == brand_id)
        .order_by(Item.view_count.desc(), Item.created_at.desc())
    )

    if limit:
        stmt = stmt.limit(limit)

    items = fetch_items(stmt, session)
    return [serialize_item(item) for item in items]


def get_contents_for_item(
    item_id: int,
    limit: int = 6,
    session=None,
) -> list[dict]:
    """
    Return content items (articles, reviews, posts) that reference a given item.

    Strategy (two-phase):
    1. Content directly linked to the item via the ``content_items`` association
       table (curated by the Article↔Item matcher) — highest confidence.
    2. Supplement with same-brand/category content to fill the remaining slots.

    Returns serialized content dicts ready for template rendering.
    """
    from sqlalchemy import or_

    from app.domains.content.models import Content
    from app.domains.content.service.query.utils import (
        build_content_stmt,
        fetch_serialized_contents,
    )

    if session is None:
        session = db.session

    # Load reference item to extract taxonomy signals
    ref_item = session.get(Item, item_id)
    if not ref_item:
        return []

    # 1. Directly linked content (via association table)
    directly_linked = [
        c for c in (ref_item.linked_contents or [])
    ]
    directly_linked_ids = {c.id for c in directly_linked}

    # Serialize directly linked content first (highest confidence)
    linked_results = []
    if directly_linked_ids:
        stmt = (
            build_content_stmt(active_only=True, published_only=True, eager_load="default")
            .where(Content.id.in_(list(directly_linked_ids)))
            .order_by(Content.view_count.desc(), Content.published_at.desc())
            .limit(limit)
        )
        linked_results = fetch_serialized_contents(stmt, session)

    if len(linked_results) >= limit:
        return linked_results[:limit]

    # 2. Supplement: same-brand or same-category content
    remaining = limit - len(linked_results)
    conditions = []

    if ref_item.brand_id:
        from app.domains.relationships import content_brands
        conditions.append(
            Content.id.in_(
                session.query(content_brands.c.content_id)
                .filter(content_brands.c.brand_id == ref_item.brand_id)
                .scalar_subquery()
            )
        )

    if ref_item.category_id:
        conditions.append(Content.category_id == ref_item.category_id)

    if conditions:
        exclude_ids = directly_linked_ids
        stmt = (
            build_content_stmt(active_only=True, published_only=True, eager_load="default")
            .where(or_(*conditions))
            .where(Content.id.notin_(list(exclude_ids)) if exclude_ids else True)
            .order_by(Content.view_count.desc(), Content.published_at.desc())
            .limit(remaining)
        )
        supplement = fetch_serialized_contents(stmt, session)
    else:
        supplement = []

    return linked_results + supplement

