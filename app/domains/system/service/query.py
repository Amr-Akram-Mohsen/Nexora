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
)

REL_MODELS = {
    "category": Category,
    "topic": Topic,
    "brand": Brand,
    "intent": IntentFacet,
    "price_tier": PriceTierFacet,
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
