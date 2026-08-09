from sqlalchemy import select, exists, and_, or_
from ...models import Content, Article, Video, VideoComment
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
            
    article_filter = and_(
        Content.object_type == "article",
        exists(
            select(1).where(
                and_(
                    Article.id == Content.object_id,
                    Article.summary.is_not(None),
                )
            )
        ),
    )

    video_filter = and_(
        Content.object_type == "video",
        exists(
            # select(1)
            select(Video.id)
            .join(VideoComment, VideoComment.video_id == Video.id)
            .where(Video.id == Content.object_id)
        ),
    )

    stmt = build_content_stmt(
        active_only=True,
        published_only=True,
        eager_load="list",
        extra_filters=[
            or_(article_filter, video_filter)
        ]
    )

    if exclude_ids:
        stmt = stmt.where(Content.id.notin_(list(exclude_ids)))
        
    stmt = apply_column_filters(stmt, filter_by_columns, filter_values)
    stmt = stmt.order_by(Content.published_at.desc())

    if rows_count is not None:
        stmt = stmt.limit(rows_count)

    return fetch_serialized_contents(stmt, session)


def _get_paginated_contents(
    filters=None, allowed_filters=None, section_id=None,
    active_only=True, published_only=True,
    sort_by=None, sort_dir=None, page=1, per_page=20, session=None, for_admin=False,
    exclude_ids=None
):
    from sqlalchemy import select, or_, func
    from ...models import Content, Article
    from app.domains.taxonomy.models import Category
    from .utils import build_content_stmt, apply_content_filters
    
    if session is None:
        from app.core.extensions import db
        session = db.session

    if filters is None:
        filters = {}

    stmt = build_content_stmt(active_only=active_only, published_only=published_only, eager_load="list")
    if section_id:
        stmt = stmt.where(Content.section_id == section_id)
        
    stmt = apply_content_filters(stmt, filters, allowed_filters=allowed_filters, session=session)
    
    if exclude_ids:
        stmt = stmt.where(Content.id.notin_(list(exclude_ids)))

    quality = None
    if for_admin:
        quality = filters.get("quality")
        if quality:
            if quality == "missing_category":
                stmt = stmt.where(or_(Content.category_id.is_(None), Content.category.has(Category.slug == "uncategorized")))
            elif quality == "missing_metadata":
                stmt = stmt.where(or_(Content.title.is_(None), Content.title == "", Content.preview_text.is_(None), Content.preview_text == ""))
            elif quality == "duplicate":
                dup_sub = select(Content.title).group_by(Content.title).having(func.count(Content.id) > 1).subquery()
                stmt = stmt.where(Content.title.in_(dup_sub))
            elif quality == "missing_entities":
                stmt = stmt.where(~Content.content_entities.any())
            elif quality == "missing_source":
                stmt = stmt.where(Content.source_id.is_(None))
            elif quality == "enrichment_pending":
                stmt = stmt.where(Content.object_type == "article", Content.object_id.in_(select(Article.id).where(Article.status == "discovered")))

        active = filters.get("active")
        if active:
            stmt = stmt.where(Content.is_active == (active.lower() == "true"))
        published = filters.get("published")
        if published:
            stmt = stmt.where(Content.is_published == (published.lower() == "true"))

    if for_admin and sort_by:
        _CONTENT_SORT_MAP = {
            "id": Content.id, "published_at": Content.published_at, "ingested_at": Content.ingested_at,
            "view_count": Content.view_count, "like_count": Content.like_count, "comment_count": Content.comment_count,
            "share_count": Content.share_count, "save_count": Content.save_count, "score": Content.score, "title": Content.title,
        }
        sort_col = _CONTENT_SORT_MAP.get(sort_by, Content.published_at)
        sort_dir = sort_dir.lower() if sort_dir and sort_dir.lower() in ("asc", "desc") else "desc"
        stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())
    else:
        if filters.get("sort") == "oldest":
            stmt = stmt.order_by(Content.published_at.asc())
        else:
            stmt = stmt.order_by(Content.published_at.desc())
            
    from app.core.extensions import db
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    
    if for_admin:
        return pagination, quality
        
    from ..content_access import assign_target_to_contents
    products = assign_target_to_contents(pagination.items, session, active_filters=filters)
    return {
        "products": products, "page": pagination.page, "pages": pagination.pages,
        "total": pagination.total, "per_page": pagination.per_page,
        "has_next": pagination.has_next, "has_prev": pagination.has_prev,
        "prev_num": getattr(pagination, "prev_num", pagination.page - 1 if pagination.has_prev else None),
        "next_num": getattr(pagination, "next_num", pagination.page + 1 if pagination.has_next else None),
    }

def get_filtered_contents(section_id=None, active_filters=None, allowed_filters=None, page=1, per_page=24, session=None, exclude_ids=None):
    """
    Handles complex filtering and pagination for section contents.
    """
    return _get_paginated_contents(
        filters=active_filters, allowed_filters=allowed_filters, section_id=section_id,
        active_only=True, published_only=True,
        page=page, per_page=per_page, session=session, for_admin=False,
        exclude_ids=exclude_ids
    )


def get_all_contents_metadata(session=None):
    from sqlalchemy import select
    from ...models import Content
    if session is None:
        from app.core.extensions import db
        session = db.session
    stmt = select(Content.id, Content.ingested_at, Content.published_at)
    return session.execute(stmt).all()


def get_candidate_contents_for_item(product, session=None):
    from sqlalchemy import select, or_
    from ...models import Content
    if session is None:
        from app.core.extensions import db
        session = db.session
    conditions = []
    if product.category_id:
        conditions.append(Content.category_id == product.category_id)
    stmt = select(Content)
    if product.brand_id:
        from app.domains.relationships import ContentEntity
        from app.domains.taxonomy.models import Entity, Brand
        brand = session.get(Brand, product.brand_id)
        if brand:
            entity = Entity.get_by_slug(brand.slug, session)
            if entity:
                stmt = stmt.join(
                    ContentEntity,
                    (ContentEntity.content_id == Content.id) & (ContentEntity.entity_id == entity.id)
                )
                conditions.append(ContentEntity.entity_id == entity.id)
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


def get_existing_content_product_links_by_contents(content_ids, session=None):
    from sqlalchemy import select
    from app.domains.relationships import content_products
    if session is None:
        from app.core.extensions import db
        session = db.session
    stmt = select(content_products.c.content_id, content_products.c.product_id).where(content_products.c.content_id.in_(content_ids))
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
    from sqlalchemy import select, func
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
            (Article.status == "discovered")
            | (
                (Article.status == "failed")
                & (
                    Article.last_enrichment_attempt.is_(None) |
                    (Article.last_enrichment_attempt < retry_threshold)
                )
            )
        )
        .order_by(func.coalesce(Article.enrichment_priority, Article.quality_score).desc(), Content.published_at.desc())
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





def get_content_paginated(filters, sort_by=None, sort_dir=None, page=1, per_page=20, session=None):
    return _get_paginated_contents(
        filters=filters,
        active_only=False,
        published_only=False,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        per_page=per_page,
        session=session,
        for_admin=True
    )
