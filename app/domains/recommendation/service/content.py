"""
Recommendation service — content queries.

All functions return serialized content dicts (same shape as the rest of the
content pipeline) so callers don't need to deal with model instances.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.extensions import db
from app.domains.content.models import Content
from app.shared.constants.core import TargetType


def get_related_contents_scored(
    content_id: int,
    limit: int = 6,
    session=None,
) -> list[dict]:
    """
    Return top-N content products most relevant to ``content_id``.
    Delegates to the content domain query service.
    """
    from app.domains.content.service.query import get_related_contents
    return get_related_contents(content_id=content_id, limit=limit, session=session)


def get_trending_contents_scored(
    limit: int = 8,
    days: int = 7,
    object_type: str | None = None,
    section_ids: list[int] | None = None,
    exclude_ids: tuple | list = None,
    session=None,
) -> list[dict]:
    """
    Return trending content ranked by recent view count.
    Delegates to the content domain query service.
    """
    from app.domains.content.service.query import get_trending_contents
    return get_trending_contents(
        limit=limit,
        days=days,
        section_ids=section_ids,
        object_type=object_type,
        exclude_ids=exclude_ids,
        session=session,
    )


def get_editors_picks(
    limit: int = 6,
    exclude_ids: tuple | list = None,
    session=None,
) -> list[dict]:
    """
    Return content with the highest editorial score (Content.score field).

    Suitable for an "Editor's Picks" homepage section. Only returns active,
    published content with score > 0.
    """
    from app.domains.content.service.query.utils import (
        build_content_stmt,
        fetch_serialized_contents,
    )

    if session is None:
        session = db.session

    stmt = (
        build_content_stmt(active_only=True, published_only=True, eager_load="default")
        .where(Content.score > 0)
    )
    
    if exclude_ids:
        stmt = stmt.where(Content.id.notin_(list(exclude_ids)))

    stmt = stmt.order_by(Content.score.desc(), Content.published_at.desc())

    if limit:
        stmt = stmt.limit(limit)

    return fetch_serialized_contents(stmt, session)
