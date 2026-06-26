"""
Application-layer recommendation query service.

Thin cached wrappers over the recommendation domain services.
Mirrors the pattern established in ``app/application/content/query_service.py``.

All functions return serialized dicts ready for template rendering.
"""
from app.infrastructure import cache
from app.core.extensions import db


# ---------------------------------------------------------------------------
# Content recommendations
# ---------------------------------------------------------------------------

@cache.memoize(timeout=3600)
def get_related_contents_for_content_cached(content_id: int, limit: int = 6) -> list:
    """
    Cached wrapper: scored related content for a content item.

    Uses multi-signal scoring (topic, brand, category, section, recency,
    popularity) with no section lock.
    """
    from app.domains.recommendation.service import get_related_contents_scored
    return get_related_contents_scored(content_id=content_id, limit=limit, session=db.session)


@cache.memoize(timeout=300)
def get_trending_contents_cached_v2(
    limit: int = 8,
    days: int = 7,
    object_type: str | None = None,
    section_ids: tuple | None = None,
    exclude_ids: tuple | None = None,
) -> list:
    """
    Cached wrapper: trending content, optionally filtered by type/section.

    Args:
        limit:       Maximum items.
        days:        Look-back window for view counting.
        object_type: 'article', 'video', or 'post' (None = all).
        section_ids: Tuple of section IDs to scope results (None = global).
    """
    from app.domains.recommendation.service import get_trending_contents_scored
    return get_trending_contents_scored(
        limit=limit,
        days=days,
        object_type=object_type,
        section_ids=list(section_ids) if section_ids else None,
        exclude_ids=exclude_ids,
        session=db.session,
    )


@cache.memoize(timeout=1800)
def get_editors_picks_cached(limit: int = 6, exclude_ids: tuple | None = None) -> list:
    """Cached wrapper: highest-scored editorial content."""
    from app.domains.recommendation.service import get_editors_picks
    return get_editors_picks(limit=limit, exclude_ids=exclude_ids, session=db.session)


# ---------------------------------------------------------------------------
# Item recommendations
# ---------------------------------------------------------------------------

@cache.memoize(timeout=3600)
def get_items_for_content_cached(content_id: int, limit: int = 8, exclude_ids: tuple | None = None) -> list:
    """
    Cached wrapper: items recommended for a content piece.

    Combines directly linked items (content_items association) with
    taxonomy-matched items (brand/category overlap).
    """
    from app.domains.recommendation.service import get_items_for_content
    return get_items_for_content(content_id=content_id, limit=limit, exclude_ids=exclude_ids, session=db.session)


@cache.memoize(timeout=600)
def get_trending_items_cached(limit: int = 8, days: int = 7, exclude_ids: tuple | None = None) -> list:
    """Cached wrapper: items ranked by recent views + clicks."""
    from app.domains.recommendation.service import get_trending_items
    return get_trending_items(limit=limit, days=days, exclude_ids=exclude_ids, session=db.session)


@cache.memoize(timeout=3600)
def get_contents_for_item_cached(item_id: int, limit: int = 6) -> list:
    """
    Cached wrapper: content (articles, reviews, posts) relevant to an item.

    Combines directly linked content (content_items association) with
    taxonomy-matched content (brand/category overlap).
    """
    from app.domains.recommendation.service import get_contents_for_item
    return get_contents_for_item(item_id=item_id, limit=limit, session=db.session)


# ---------------------------------------------------------------------------
# Brand recommendations
# ---------------------------------------------------------------------------

@cache.memoize(timeout=1800)
def get_trending_brands_cached(limit: int = 6, days: int = 7) -> list:
    """
    Cached wrapper: brands ranked by recent content view-count sum.

    Returns mapping rows with ``slug``, ``name``, ``recent_views``.
    """
    from app.domains.taxonomy.service.query import get_trending_brands
    return get_trending_brands(limit=limit, days=days)


# ---------------------------------------------------------------------------
# Filter-aware context recommendations
# ---------------------------------------------------------------------------

@cache.memoize(timeout=300)
def get_popular_contents_cached(
    section_id: int | None = None,
    category_slugs: tuple | None = None,
    brand_slugs: tuple | None = None,
    intent_slugs: tuple | None = None,
    limit: int = 6,
) -> list[dict]:
    """
    Cached filter-aware query for popular content matching active filters.
    """
    from app.domains.content.service.query.trending import get_popular_contents
    return get_popular_contents(
        section_id=section_id,
        category_slugs=category_slugs,
        brand_slugs=brand_slugs,
        intent_slugs=intent_slugs,
        limit=limit,
        session=db.session
    )


@cache.memoize(timeout=300)
def get_popular_items_cached(
    category_slugs: tuple | None = None,
    brand_slugs: tuple | None = None,
    limit: int = 6,
) -> list[dict]:
    """
    Cached filter-aware query for popular items/deals matching active filters.
    """
    from app.domains.item.service.query import get_popular_items
    return get_popular_items(
        category_slugs=category_slugs,
        brand_slugs=brand_slugs,
        limit=limit,
        session=db.session
    )


