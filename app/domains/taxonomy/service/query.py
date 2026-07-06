from app.core.extensions import db
from ...content.models import Content
from sqlalchemy import func, select
from app.infrastructure import cache
from app.domains.relationships import content_brands
from ..models import (
    Category,
    Brand,
    Topic,
    IntentFacet,
    PriceTierFacet,
    Section,
    AttributeFacet,
)

REL_MODELS = {
    "category": Category,
    "topic": Topic,
    "brand": Brand,
    "intent": IntentFacet,
    "price_tier": PriceTierFacet,
    "attributes": AttributeFacet,
}


def build_filter_projection(model):
    return (
        model.slug.label("slug"),
        model.name.label("name"),
    )


def apply_content_section_filters(
    stmt,
    model,
    section_slug,
    limit=20,
):
    return (
        stmt.join(Section, Section.id == Content.section_id)
        .where(
            func.lower(Section.slug) == func.lower(section_slug),
            Content.is_active,
            Content.is_published,
        )
        .group_by(
            model.id,
            model.slug,
            model.name,
        )
        .order_by(func.count(Content.id).desc())
        .limit(limit)
    )


def execute_mapped_query(stmt, session=None):
    if session is None:
        session = db.session
    rows = session.execute(stmt).mappings().all()
    return [dict(row) for row in rows]

def get_taxonomy_mappings(model_class, used_in_model=None, used_in_column=None, session=None):
    """
    Fetches basic mappings (id, name, slug) for any taxonomy model.
    Optionally filters only those used in a specific model/column.
    """
    if session is None:
        session = db.session
    stmt = select(model_class.id, model_class.name, model_class.slug)
    
    if used_in_model is not None and used_in_column is not None:
        stmt = stmt.where(model_class.id.in_(select(used_in_column).distinct()))
        
    rows = session.execute(stmt.order_by(model_class.name)).mappings().all()
    return [dict(r) for r in rows]

def get_taxonomy_content_stats(entity_id, field=None, relationship_table=None, foreign_key_col=None, session=None):
    """
    Dynamically calculates content breakdown, engagement stats, and top contents for a given taxonomy entity.
    """
    if session is None:
        session = db.session
    
    from app.domains.content.models import Content
    
    breakdown_stmt = select(Content.object_type, func.count(Content.id))
    eng_stmt = select(func.sum(Content.view_count), func.sum(Content.like_count), func.sum(Content.share_count))
    top_stmt = select(Content).order_by(Content.view_count.desc()).limit(5)
    
    if relationship_table is not None and foreign_key_col is not None:
        breakdown_stmt = breakdown_stmt.join(relationship_table, relationship_table.c.content_id == Content.id).where(foreign_key_col == entity_id).group_by(Content.object_type)
        eng_stmt = eng_stmt.join(relationship_table, relationship_table.c.content_id == Content.id).where(foreign_key_col == entity_id)
        top_stmt = top_stmt.join(relationship_table, relationship_table.c.content_id == Content.id).where(foreign_key_col == entity_id)
    elif field is not None:
        breakdown_stmt = breakdown_stmt.where(field == entity_id).group_by(Content.object_type)
        eng_stmt = eng_stmt.where(field == entity_id)
        top_stmt = top_stmt.where(field == entity_id)
    else:
        raise ValueError("Must provide either a field or a relationship_table/foreign_key_col pair.")
        
    type_breakdown = session.execute(breakdown_stmt).all()
    engagement = session.execute(eng_stmt).first()
    top_contents = session.execute(top_stmt).scalars().all()
    
    return type_breakdown, engagement, top_contents


@cache.memoize(timeout=3600)
def get_relationships_for_section(section_slug, rel_name, limit=20, session=None):
    rel_model = REL_MODELS.get(rel_name, None)
    if not rel_model:
        raise ValueError("Invalid relationship name")

    stmt = select(*build_filter_projection(rel_model)).join(rel_model.contents)

    stmt = apply_content_section_filters(
        stmt=stmt,
        model=rel_model,
        section_slug=section_slug,
        limit=limit,
    )

    return execute_mapped_query(stmt, session)


@cache.memoize(timeout=3600)
def get_types_for_section(section_slug, session=None):
    stmt = (
        select(Content.object_type)
        .join(Section, Section.id == Content.section_id)
        .where(func.lower(Section.slug) == func.lower(section_slug))
        .group_by(Content.object_type)
    )
    rows = execute_mapped_query(stmt, session)
    return [
        {"slug": r["object_type"].lower(), "name": r["object_type"].title()}
        for r in rows
        if r.get("object_type")
    ]


@cache.memoize(timeout=3600)
def get_popular_general_topics(limit=4, session=None):
    stmt = select(*build_filter_projection(Topic)).limit(limit)
    return execute_mapped_query(stmt, session)


@cache.memoize(timeout=3600)
def get_popular_brands(limit=5, session=None):
    """
    Return brands ordered by the number of linked items (descending).
    Previously returned brands in arbitrary row order.
    """
    from app.domains.item.models import Item

    stmt = (
        select(*build_filter_projection(Brand), func.count(Item.id).label("item_count"))
        .join(Item, Item.brand_id == Brand.id, isouter=True)
        .where(Brand.is_active.is_(True))
        .group_by(Brand.id, Brand.slug, Brand.name)
        .order_by(func.count(Item.id).desc())
        .limit(limit)
    )
    return execute_mapped_query(stmt, session)


@cache.memoize(timeout=3600)
def get_active_sections(session=None):
    stmt = select(*build_filter_projection(Section)).where(Section.is_active)
    return execute_mapped_query(stmt, session)


def get_section_by_slug(slug, session=None):
    if session is None:
        session = db.session
    stmt = select(Section).where(Section.slug == slug, Section.is_active)
    return session.execute(stmt).scalars().first()


@cache.memoize(timeout=1800)
def get_trending_brands(limit: int = 6, days: int = 7, session=None):
    """
    Return brands ranked by the sum of view counts on recently published content.

    Brands whose content got the most views in the past ``days`` days appear
    first — a reliable signal of editorial trending momentum.

    Args:
        limit: Maximum number of brands to return.
        days:  Look-back window in days.
        session: Optional DB session context.

    Returns:
        List of mapping rows with ``slug``, ``name``, and ``recent_views``.
    """
    from datetime import datetime, timedelta, timezone
    from app.domains.content.models import Content

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            *build_filter_projection(Brand),
            func.sum(Content.view_count).label("recent_views"),
        )
        .join(content_brands, Brand.id == content_brands.c.brand_id)
        .join(Content, Content.id == content_brands.c.content_id)
        .where(
            Brand.is_active.is_(True),
            Content.is_active.is_(True),
            Content.is_published.is_(True),
            Content.published_at >= cutoff,
        )
        .group_by(Brand.id, Brand.slug, Brand.name)
        .order_by(func.sum(Content.view_count).desc())
        .limit(limit)
    )
    return execute_mapped_query(stmt, session)


def _get_distinct_item_taxonomy(model_class, session=None):
    from app.domains.item.models import Item
    stmt = (
        select(model_class.slug, model_class.name)
        .join(Item)
        .distinct()
        .order_by(model_class.name)
    )
    return execute_mapped_query(stmt, session)


@cache.memoize(timeout=3600)
def get_distinct_item_categories(session=None):
    return _get_distinct_item_taxonomy(Category, session)


@cache.memoize(timeout=3600)
def get_distinct_item_brands(session=None):
    return _get_distinct_item_taxonomy(Brand, session)


def get_attributes_for_section(section_slug, category_slugs=None, limit=20, session=None):
    """
    Retrieves active attributes for a section, optionally filtered by selected categories.
    """
    if category_slugs:
        if isinstance(category_slugs, str):
            category_slugs = (category_slugs,)
        elif isinstance(category_slugs, list):
            category_slugs = tuple(sorted([s for s in category_slugs if s]))
    else:
        category_slugs = None

    return _cached_attributes_for_section(section_slug, category_slugs, limit, session)


@cache.memoize(timeout=3600)
def _cached_attributes_for_section(section_slug, category_slugs_tuple, limit, session=None):
    from app.domains.taxonomy.models import AttributeFacet, Category

    stmt = select(*build_filter_projection(AttributeFacet)).join(AttributeFacet.contents)

    if category_slugs_tuple:
        # Resolve selected categories to load parent-child hierarchies
        from sqlalchemy.orm import selectinload

        if session is None:
            session = db.session

        categories = session.execute(
            select(Category)
            .options(selectinload(Category.children))
            .where(
                func.lower(Category.slug).in_(
                    [func.lower(s) for s in category_slugs_tuple]
                )
            )
        ).scalars().all()

        category_ids = set()
        for cat in categories:
            category_ids.add(cat.id)
            # Add parent category if it exists (e.g. Smartphones -> Electronics)
            if cat.parent_id:
                category_ids.add(cat.parent_id)
            # Add child categories if any exist (e.g. Electronics -> Smartphones, Laptops)
            if cat.children:
                for child in cat.children:
                    category_ids.add(child.id)

        stmt = stmt.where(AttributeFacet.category_id.in_(list(category_ids)))

    stmt = apply_content_section_filters(
        stmt=stmt,
        model=AttributeFacet,
        section_slug=section_slug,
        limit=limit,
    )

    return execute_mapped_query(stmt, session)

def paginate_taxonomy_entity(model, page, per_page, search="", status=None, health=None, field_name=None):
    """Generic pagination utility for taxonomy entities supporting search, status, and health checks."""
    from app.domains.content.models import Content
    from app.domains.item.models import Item
    from app.domains.relationships import content_brands, content_topics, content_attributes
    from app.domains.taxonomy.models import Category, Brand, Topic, Section, AttributeFacet
    
    stmt = select(model).order_by(model.name.asc())
    if search:
        stmt = stmt.where(model.name.ilike(f"%{search}%"))
        
    if hasattr(model, 'is_active'):
        if status == "1":
            stmt = stmt.where(model.is_active == True)
        elif status == "0":
            stmt = stmt.where(model.is_active == False)
        
    if health:
        cond_content = None
        cond_item = None
        
        if model == Category:
            cond_content = db.session.query(Content.id).filter(Content.category_id == Category.id).exists()
            cond_item = db.session.query(Item.id).filter(Item.category_id == Category.id).exists()
        elif model == Brand:
            cond_content = db.session.query(content_brands.c.content_id).filter(content_brands.c.brand_id == Brand.id).exists()
            cond_item = db.session.query(Item.id).filter(Item.brand_id == Brand.id).exists()
        elif model == Topic:
            cond_content = db.session.query(content_topics.c.content_id).filter(content_topics.c.topic_id == Topic.id).exists()
        elif model == Section:
            cond_content = db.session.query(Content.id).filter(Content.section_id == Section.id).exists()
        elif model == AttributeFacet:
            cond_content = db.session.query(content_attributes.c.content_id).filter(content_attributes.c.attribute_id == AttributeFacet.id).exists()
        elif field_name:
            field = getattr(Content, field_name)
            cond_content = db.session.query(Content.id).filter(field == model.id).exists()

        if health == "unused":
            if cond_content is not None:
                stmt = stmt.where(~cond_content)
            if cond_item is not None:
                stmt = stmt.where(~cond_item)
        elif health == "inactive-linked" and hasattr(model, 'is_active'):
            stmt = stmt.where(model.is_active == False)
            if cond_content is not None and cond_item is not None:
                stmt = stmt.where(cond_content | cond_item)
            elif cond_content is not None:
                stmt = stmt.where(cond_content)
                
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)
