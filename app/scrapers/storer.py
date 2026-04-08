# app/scrapers/storer.py
"""
Stores a cleaned article dict into the Article model.
Full data flow: section_slug → Section (M2M)
               category_slug → Category (FK)
               brand_slugs   → Brand(s) (M2M via article_brands)
               topic_slugs   → Topic(s) (M2M via article_topics)

All lookups use get-or-create so the DB is self-healing:
missing Sections/Categories will be created on first encounter.
"""
import logging
from slugify import slugify
from sqlalchemy.exc import IntegrityError
from app.models import db, Article, Section, Category, Brand, Topic

logger = logging.getLogger(__name__)

DEFAULT_CATEGORY_SLUG = "general"


# ── Lookup / auto-create helpers ─────────────────────────────────

def _get_section(slug: str) -> Section | None:
    if not slug:
        return None
    return Section.query.filter_by(slug=slug, is_active=True).first()


def _get_or_create_category(slug: str) -> Category:
    slug = slug or DEFAULT_CATEGORY_SLUG
    cat = Category.query.filter_by(slug=slug).first()
    if not cat:
        name = slug.replace("-", " ").title()
        cat = Category(name=name, slug=slug)
        db.session.add(cat)
        db.session.flush()
    return cat


def _get_or_create_brand(slug: str) -> Brand:
    brand = Brand.query.filter_by(slug=slug).first()
    if not brand:
        name = slug.replace("-", " ").title()
        brand = Brand(name=name, slug=slug)
        db.session.add(brand)
        db.session.flush()
    return brand


def _get_or_create_topic(slug: str) -> Topic:
    topic = Topic.query.filter_by(slug=slug).first()
    if not topic:
        name = slug.replace("-", " ").title()
        topic = Topic(name=name, slug=slug)
        db.session.add(topic)
        db.session.flush()
    return topic


# ── Public entry point ────────────────────────────────────────────

def store_article(data: dict) -> Article | None:
    """
    Store one cleaned article.

    Expected data dict keys:
      title         (required)
      url           (required, used for dedup)
      description   (optional)
      image_url     (optional)
      published_at  (optional datetime)
      source_name   (optional str)
      section_slug  (optional str)  → linked via article_sections M2M
      category_slug (optional str)  → sets Article.category_id FK
      brand_slugs   (optional list) → linked via article_brands M2M
      topic_slugs   (optional list) → linked via article_topics M2M

    Returns the new Article or None if skipped/error.
    """
    url = (data.get("url") or "").strip()
    title = (data.get("title") or "").strip()
    source_name = (data.get("source_name") or "").strip()

    if not url or not title:
        return None

    try:
        # ── Fast dedup check (by URL and by Source+Title) ─────────────
        if Article.query.filter_by(url=url).first():
            return None
            
        if source_name and Article.query.filter_by(source_name=source_name, title=title).first():
            logger.debug("[Storer] Skipping duplicate (Source+Title): %s | %s", source_name, title)
            return None

        # ── Resolve FK: Category ─────────────────────────────────────
        category_slug = data.get("category_slug") or DEFAULT_CATEGORY_SLUG
        category = _get_or_create_category(category_slug)

        # ── Build Article record ─────────────────────────────────────
        article = Article(
            title=title,
            description=data.get("description") or None,
            content=data.get("content") or None,
            url=url,
            image_url=data.get("image_url") or None,
            published_at=data.get("published_at"),
            source_name=source_name or None,
            category_id=category.id,
            is_active=True,
        )
        db.session.add(article)

        # ── Resolve M2M: Section ─────────────────────────────────────
        section_slug = data.get("section_slug", "")
        if section_slug:
            section = _get_section(section_slug)
            if section:
                article.sections.append(section)

        # ── Resolve M2M: Brands ──────────────────────────────────────
        for slug in (data.get("brand_slugs") or []):
            slug = slugify(slug)
            if slug:
                article.brands.append(_get_or_create_brand(slug))

        # ── Resolve M2M: Topics ──────────────────────────────────────
        for slug in (data.get("topic_slugs") or []):
            slug = slugify(slug)
            if slug:
                article.topics.append(_get_or_create_topic(slug))

        db.session.commit()
        return article

    except IntegrityError:
        db.session.rollback()
        logger.debug("[Storer] Integrity error (race condition?): %s", url)
        return None
    except Exception:
        db.session.rollback()
        logger.exception("[Storer] Error storing article: %s", url)
        return None
