from app.core.extensions import db
from ...content.models import Content
from ..models import Category, Section, Brand, Topic
from sqlalchemy import func
from app.infrastructure import cache
from app.domains.relationships import content_brands


@cache.memoize(timeout=3600)
def get_active_brands_for_section(section_slug, limit=20):
    """
    Returns brands that have at least one content in the given section.
    Uses explicit join with the association table to avoid SQLAlchemy
    relationship chain ambiguity.
    """
    return (
        db.session.query(Brand)
        .join(content_brands, Brand.id == content_brands.c.brand_id)
        .join(Content, Content.id == content_brands.c.content_id)
        .join(Section, Section.id == Content.section_id)
        .filter(func.lower(Section.slug) == func.lower(section_slug))
        .group_by(Brand.id)
        .order_by(func.count(Content.id).desc())
        .limit(limit)
        .all()
    )

@cache.memoize(timeout=3600)
def get_active_topics_for_section(section_slug, limit=20):
    """
    Returns topics that have at least one content in the given section.
    Uses explicit join with the association table for reliability.
    """
    from app.domains.relationships import content_topics
    return (
        db.session.query(Topic)
        .join(content_topics, Topic.id == content_topics.c.topic_id)
        .join(Content, Content.id == content_topics.c.content_id)
        .join(Section, Section.id == Content.section_id)
        .filter(func.lower(Section.slug) == func.lower(section_slug))
        .group_by(Topic.id)
        .order_by(func.count(Content.id).desc())
        .limit(limit)
        .all()
    )
@cache.memoize(timeout=3600)
def get_active_categories_for_section(section_slug, limit=20):
    """
    Returns categories that have at least one content in the given section.
    Contents have a direct many-to-one category_id column.
    """
    return (
        db.session.query(Category)
        .join(Content, Content.category_id == Category.id)
        .join(Section, Section.id == Content.section_id)
        .filter(func.lower(Section.slug) == func.lower(section_slug))
        .group_by(Category.id)
        .order_by(func.count(Content.id).desc())
        .limit(limit)
        .all()
    )

@cache.memoize(timeout=3600)
def get_popular_general_topics():
    return (
        db.session.query(Topic.slug, Topic.name)
        .all()
    )
@cache.memoize(timeout=3600)
def get_popular_brands(limit=5):
    return (
        db.session.query(Brand.slug, Brand.name)
        .limit(limit)
        .all()
    )

@cache.memoize(timeout=3600)
def get_active_sections():
    return (
        db.session.query(Section.slug, Section.name)
        .filter_by(is_active=True)
        # .order_by(Section.sort_order)
        .all()
    )
def get_section_by_slug(slug):
    return Section.query.filter(
        Section.slug == slug,
        Section.is_active == True
    ).first()
def get_distinct_item_categories():
    from app.domains.item.models import Item
    return Category.query.join(Item).distinct().all()

def get_distinct_item_brands():
    from app.domains.item.models import Item
    return Brand.query.join(Item).distinct().all()

def get_allowed_filters(section):
    """
    Returns the set of allowed filters for a given section.
    This is a domain rule.
    """
    return set(section.allowed_filters or [])
