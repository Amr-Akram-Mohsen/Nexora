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

    cats = [f for f in active_filters.get("category", []) if f]
    if cats and "category" in allowed_filters:
        category_objs = session.execute(
            select(Category)
            .options(selectinload(Category.children))
            .where(Category.slug.in_(cats))
        ).scalars().all()
        
        cat_ids = set()
        for cat in category_objs:
            cat_ids.add(cat.id)
            if cat.children:
                for child in cat.children:
                    cat_ids.add(child.id)
        stmt = stmt.where(Content.category_id.in_(list(cat_ids)))

    topics = [f for f in active_filters.get("topic", []) if f]
    if topics and "topic" in allowed_filters:
        stmt = stmt.where(Content.topics.any(Topic.slug.in_(topics)))

    brands = [f for f in active_filters.get("brand", []) if f]
    if brands and "brand" in allowed_filters:
        stmt = stmt.where(Content.brands.any(Brand.slug.in_(brands)))

    intents = [f for f in active_filters.get("intent", []) if f]
    if intents and "intent" in allowed_filters:
        from app.domains.taxonomy.models import IntentFacet
        stmt = stmt.where(Content.intent.has(IntentFacet.slug.in_(intents)))

    price_tiers = [f for f in active_filters.get("price_tier", []) if f]
    if price_tiers and "price_tier" in allowed_filters:
        from app.domains.taxonomy.models import PriceTierFacet
        stmt = stmt.where(Content.price_tier.has(PriceTierFacet.slug.in_(price_tiers)))

    types = [f for f in active_filters.get("type", []) if f]
    if types and "type" in allowed_filters:
        stmt = stmt.where(Content.object_type.in_(types))

    attributes = [f for f in active_filters.get("attributes", []) if f]
    if attributes and "attributes" in allowed_filters:
        from app.domains.taxonomy.models import AttributeFacet
        stmt = stmt.where(Content.attributes.any(AttributeFacet.slug.in_(attributes)))

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
    stmt = select(Content.id, Content.updated_at, Content.published_at)
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
