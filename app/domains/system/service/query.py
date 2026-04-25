from app.core.extensions import db
from app.domains.article.models import Article
from ..models import Category, Section, Brand, Topic
# from app.domains.system.models import Category, Section, Brand, Topic
from sqlalchemy import func
from app.core.extensions import cache
from app.domains.relationships import article_brands


@cache.memoize(timeout=3600)
def get_active_brands_for_section(section_slug, limit=20):
    """
    Returns brands that have at least one article in the given section.
    Uses explicit join with the association table to avoid SQLAlchemy
    relationship chain ambiguity.
    """
    return (
        db.session.query(Brand)
        .join(article_brands, Brand.id == article_brands.c.brand_id)
        .join(Article, Article.id == article_brands.c.article_id)
        .join(Section, Section.id == Article.section_id)
        .filter(func.lower(Section.slug) == func.lower(section_slug))
        .group_by(Brand.id)
        .order_by(func.count(Article.id).desc())
        .limit(limit)
        .all()
    )

@cache.memoize(timeout=3600)
def get_active_topics_for_section(section_slug, limit=20):
    """
    Returns topics that have at least one article in the given section.
    Uses explicit join with the association table for reliability.
    """
    from app.domains.relationships import article_topics
    return (
        db.session.query(Topic)
        .join(article_topics, Topic.id == article_topics.c.topic_id)
        .join(Article, Article.id == article_topics.c.article_id)
        .join(Section, Section.id == Article.section_id)
        .filter(func.lower(Section.slug) == func.lower(section_slug))
        .group_by(Topic.id)
        .order_by(func.count(Article.id).desc())
        .limit(limit)
        .all()
    )
@cache.memoize(timeout=3600)
def get_active_categories_for_section(section_slug, limit=20):
    """
    Returns categories that have at least one article in the given section.
    Articles have a direct many-to-one category_id column.
    """
    return (
        db.session.query(Category)
        .join(Article, Article.category_id == Category.id)
        .join(Section, Section.id == Article.section_id)
        .filter(func.lower(Section.slug) == func.lower(section_slug))
        .group_by(Category.id)
        .order_by(func.count(Article.id).desc())
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
