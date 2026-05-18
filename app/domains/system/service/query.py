from app.core.extensions import db
from ...content.models import Content
from sqlalchemy import func, select
from app.infrastructure import cache
from app.domains.relationships import content_brands
from app.domains.system.models import (
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


def execute_mapped_query(stmt):
    return db.session.execute(stmt).mappings().all()


@cache.memoize(timeout=3600)
def get_relationships_for_section(section_slug, rel_name, limit=20):
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

    return execute_mapped_query(stmt)


@cache.memoize(timeout=3600)
def get_types_for_section(section_slug):
    stmt = (
        select(Content.object_type)
        .join(Section, Section.id == Content.section_id)
        .where(func.lower(Section.slug) == func.lower(section_slug))
        .group_by(Content.object_type)
    )
    rows = execute_mapped_query(stmt)
    return [
        {"slug": r.object_type.lower(), "name": r.object_type.title()}
        for r in rows
        if r.object_type
    ]


@cache.memoize(timeout=3600)
def get_popular_general_topics(limit=4):
    stmt = select(*build_filter_projection(Topic)).limit(limit)
    return execute_mapped_query(stmt)


@cache.memoize(timeout=3600)
def get_popular_brands(limit=5):
    stmt = select(*build_filter_projection(Brand)).limit(limit)

    return execute_mapped_query(stmt)


@cache.memoize(timeout=3600)
def get_active_sections():
    stmt = select(*build_filter_projection(Section)).where(Section.is_active)
    return execute_mapped_query(stmt)


def get_section_by_slug(slug):
    return Section.query.filter(Section.slug == slug, Section.is_active).first()


def get_distinct_item_categories():
    from app.domains.item.models import Item

    return Category.query.join(Item).distinct().all()


def get_distinct_item_brands():
    from app.domains.item.models import Item

    return Brand.query.join(Item).distinct().all()


def get_attributes_for_section(section_slug, category_slugs=None, limit=20):
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

    return _cached_attributes_for_section(section_slug, category_slugs, limit)


@cache.memoize(timeout=3600)
def _cached_attributes_for_section(section_slug, category_slugs_tuple, limit):
    from app.domains.system.models import AttributeFacet, Category

    stmt = select(*build_filter_projection(AttributeFacet)).join(AttributeFacet.contents)

    if category_slugs_tuple:
        # Resolve selected categories to load parent-child hierarchies
        categories = db.session.execute(
            select(Category).where(func.lower(Category.slug).in_([func.lower(s) for s in category_slugs_tuple]))
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

    return execute_mapped_query(stmt)

