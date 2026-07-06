from sqlalchemy import select
from ...models import Content

def get_contents_render(
    filter_by_columns: tuple = ("section",),
    filter_values: tuple = (None,),
    rows_count=None,
    exclude_ids=None,
    session=None,
):
    from .utils import build_content_stmt, apply_column_filters, fetch_serialized_contents
    
    if session is None:
        from app.core.extensions import db
        session = db.session
        
    stmt = build_content_stmt(active_only=True, published_only=True, eager_load="list")
    
    if exclude_ids:
        stmt = stmt.where(Content.id.notin_(list(exclude_ids)))
        
    stmt = apply_column_filters(stmt, filter_by_columns, filter_values)
    stmt = stmt.order_by(Content.published_at.desc())

    if rows_count is not None:
        stmt = stmt.limit(rows_count)

    return fetch_serialized_contents(stmt, session)


def get_filtered_contents(
    section_id=None, active_filters=None, allowed_filters=None, page=1, per_page=24, session=None
):
    """
    Handles complex filtering and pagination for section contents.
    """
    from app.domains.taxonomy.models import Category, Brand, Topic
    from .utils import build_content_stmt
    from app.core.extensions import db
    from sqlalchemy.orm import selectinload
    
    if session is None:
        session = db.session

    if active_filters is None:
        active_filters = {}
    if allowed_filters is None:
        allowed_filters = []

    stmt = build_content_stmt(active_only=True, published_only=True, eager_load="list")
    stmt = stmt.where(Content.section_id == section_id)

    from .utils import apply_content_filters
    stmt = apply_content_filters(stmt, active_filters, allowed_filters, session=session)

    if active_filters.get("sort") == "oldest":
        stmt = stmt.order_by(Content.published_at.asc())
    else:
        stmt = stmt.order_by(Content.published_at.desc())

    # Standard 2.0 statement pagination using Flask-SQLAlchemy db.paginate
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    from ..content_access import assign_target_to_contents
    items = assign_target_to_contents(
        pagination.items,
        session
    )

    return {
        "items": items,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "per_page": pagination.per_page,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    }


def get_all_contents_metadata(session=None):
    from sqlalchemy import select
    from ...models import Content
    if session is None:
        from app.core.extensions import db
        session = db.session
    stmt = select(Content.id, Content.ingested_at, Content.published_at)
    return session.execute(stmt).all()


def get_candidate_contents_for_item(item, session=None):
    from sqlalchemy import select, or_
    from ...models import Content
    if session is None:
        from app.core.extensions import db
        session = db.session
    conditions = []
    if item.category_id:
        conditions.append(Content.category_id == item.category_id)
    stmt = select(Content)
    if item.brand_id:
        from app.domains.relationships import content_brands
        stmt = stmt.outerjoin(content_brands, Content.id == content_brands.c.content_id)
        conditions.append(content_brands.c.brand_id == item.brand_id)
    if not conditions:
        return []
    stmt = stmt.where(or_(*conditions)).order_by(Content.published_at.desc()).limit(1000)
    return session.execute(stmt).scalars().all()


def get_contents_for_matching_batch(offset, batch_size, cutoff=None, cutoff_naive=None, session=None):
    from sqlalchemy import select, or_
    from ...models import Content
    if session is None:
        from app.core.extensions import db
        session = db.session
    stmt = select(Content).where(Content.is_active == True)
    if cutoff and cutoff_naive:
        stmt = stmt.where(or_(Content.ingested_at >= cutoff, Content.ingested_at >= cutoff_naive))
    stmt = stmt.offset(offset).limit(batch_size)
    return session.execute(stmt).scalars().all()


def get_existing_content_item_links_by_contents(content_ids, session=None):
    from sqlalchemy import select
    from app.domains.relationships import content_items
    if session is None:
        from app.core.extensions import db
        session = db.session
    stmt = select(content_items.c.content_id, content_items.c.item_id).where(content_items.c.content_id.in_(content_ids))
    return session.execute(stmt).all()


def get_contents_by_ids(content_ids, session=None):
    from sqlalchemy import select
    from ...models import Content
    from .options import CONTENT_LIST_EAGER_LOADS
    if session is None:
        from app.core.extensions import db
        session = db.session
    if not content_ids:
        return []
    stmt = (
        select(Content)
        .options(*CONTENT_LIST_EAGER_LOADS)
        .where(Content.id.in_(content_ids))
    )
    return session.execute(stmt).scalars().all()


def get_unscraped_articles(limit, retry_threshold, session=None):
    from sqlalchemy import select
    from ...models import Article, Content
    if session is None:
        from app.core.extensions import db
        session = db.session
    stmt = (
        select(Article)
        .join(
            Content,
            (Content.object_type == "article")
            & (Content.object_id == Article.id)
            & (Content.is_active),
        )
        .where(
            (Article.status == "pending")
            | (
                (Article.status == "failed")
                & (Article.last_enrichment_attempt < retry_threshold)
            )
        )
        .order_by(Content.published_at.desc())
        .limit(limit)
    )
    return session.execute(stmt).scalars().all()


def get_content_by_object(object_type, object_id, session=None):
    from sqlalchemy import select
    from ...models import Content
    if session is None:
        from app.core.extensions import db
        session = db.session
    stmt = select(Content).where(
        Content.object_type == object_type,
        Content.object_id == object_id
    )
    return session.execute(stmt).scalars().first()


def get_markdown_only_articles(limit, session=None):
    """
    Return articles that have been scraped (content_markdown is set)
    but have not yet been processed into content_blocks.
    These are targeted FIRST during enrich-articles runs before normal
    unscraped articles are processed.
    """
    from sqlalchemy import select
    from ...models import Article, Content
    if session is None:
        from app.core.extensions import db
        session = db.session
    stmt = (
        select(Article)
        .join(
            Content,
            (Content.object_type == "article")
            & (Content.object_id == Article.id)
            & (Content.is_active),
        )
        .where(
            Article.content_markdown.is_not(None),
            Article.content_blocks.is_(None),
            Article.status == "complete",  # only fully-scraped articles
        )
        .order_by(Content.published_at.desc())
        .limit(limit)
    )
    return session.execute(stmt).scalars().all()


def get_content_paginated(filters, sort_by=None, sort_dir=None, page=1, per_page=20, session=None):
    from sqlalchemy import select, or_, func
    from ...models import Content, Article
    from app.domains.taxonomy.models import Category
    from .utils import build_content_stmt, apply_content_filters
    
    if session is None:
        from app.core.extensions import db
        session = db.session

    _CONTENT_SORT_MAP = {
        "id": Content.id,
        "published_at": Content.published_at,
        "ingested_at": Content.ingested_at,
        "view_count": Content.view_count,
        "like_count": Content.like_count,
        "comment_count": Content.comment_count,
        "share_count": Content.share_count,
        "save_count": Content.save_count,
        "score": Content.score,
        "title": Content.title,
    }
    
    sort_col = _CONTENT_SORT_MAP.get(sort_by, Content.published_at)
    sort_dir = sort_dir.lower() if sort_dir and sort_dir.lower() in ("asc", "desc") else "desc"

    stmt = build_content_stmt(active_only=False, published_only=False, eager_load="list")
    
    stmt = apply_content_filters(stmt, filters, session=session)

    quality = filters.get("quality")
    if quality:
        if quality == "missing_category":
            stmt = stmt.where(or_(Content.category_id.is_(None), Content.category.has(Category.slug == "uncategorized")))
        elif quality == "missing_metadata":
            stmt = stmt.where(or_(Content.title.is_(None), Content.title == "", Content.preview_text.is_(None), Content.preview_text == ""))
        elif quality == "duplicate":
            dup_sub = (
                select(Content.title)
                .group_by(Content.title)
                .having(func.count(Content.id) > 1)
            ).subquery()
            stmt = stmt.where(Content.title.in_(dup_sub))
        elif quality == "missing_topics":
            stmt = stmt.where(~Content.topics.any())
        elif quality == "missing_brands":
            stmt = stmt.where(~Content.brands.any())
        elif quality == "missing_source":
            stmt = stmt.where(Content.source_id.is_(None))
        elif quality == "enrichment_failed":
            stmt = stmt.where(Content.object_type == "article", Content.object_id.in_(select(Article.id).where(Article.status == "failed")))
            
    active = filters.get("active")
    if active:
        stmt = stmt.where(Content.is_active == (active.lower() == "true"))
    published = filters.get("published")
    if published:
        stmt = stmt.where(Content.is_published == (published.lower() == "true"))
        
    stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())
    
    from app.core.extensions import db
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    return pagination, quality
