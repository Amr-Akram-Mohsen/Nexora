# app/domains/article/ingestion.py
"""
Stores a cleaned article dict into the Article model.
Orchestrates enrichment via EnrichmentEngine before insertion.
"""
import logging
from sqlalchemy.exc import IntegrityError
from app.core.extensions import db
from .models import Article
from app.domains.system.models import (
    Section, Category, Brand, Topic, Source,
    GenderFacet, IntentFacet, PriceTierFacet, AttributeFacet
)
from app.integrations.cleaner import clean_article_data

from app.shared.utils.slug import generate_slug

logger = logging.getLogger(__name__)

def _resolve_taxonomy(data: dict) -> tuple[Section, Category]:
    """Resolve Section & Category with fallback values."""
    section_slug = data.get("section_slug") or "news"
    section = Section.get_by_slug(section_slug, session=db.session)
    if not section:
        section = Section.get_by_slug("news", session=db.session)

    category_slug = data.get("category_slug") or "uncategorized"
    category = Category.get_by_slug(category_slug, session=db.session)
    if not category:
        category = Category.get_by_slug("uncategorized", session=db.session)
    
    return section, category

def _apply_many_to_many(article: Article, data: dict):
    """Link Topics, Brands, Attributes, and Sources from raw or cleaned data."""
    # 1. Topics
    for t_slug in (data.get("topic_slugs") or []):
        topic = Topic.get_by_slug(t_slug, session=db.session)
        if topic:
            article.add_topic(topic)

    # 2. Brands
    for b_slug in (data.get("brand_slugs") or []):
        brand = Brand.get_by_slug(b_slug, session=db.session)
        if brand:
            article.add_brand(brand)

    # 3. Attributes (usually from facets dict)
    facets_data = data.get("facets") or {}
    for attr_slug in (facets_data.get("attributes") or []):
        attr = AttributeFacet.get_by_slug(attr_slug, session=db.session)
        if attr:
            article.add_attribute(attr)

    # 4. Sources
    source_name = data.get("source_name")
    url = data.get("url")
    if source_name and url:
        source_slug = generate_slug(source_name)
        source = Source.get_by_slug(source_slug, session=db.session)
        if source:
            article.add_source(source, url)

def _apply_single_facets(article: Article, data: dict):
    """Link 1-M facets like Gender, Intent, and Price Tier."""
    facets_data = data.get("facets") or {}

    # Gender
    g_slug = facets_data.get("gender")
    if g_slug:
        gender = GenderFacet.get_by_slug(g_slug, session=db.session)
        if gender:
            article.gender_id = gender.id

    # Intent
    i_slug = facets_data.get("intent")
    if i_slug:
        intent = IntentFacet.get_by_slug(i_slug, session=db.session)
        if intent:
            article.intent_id = intent.id

    # Price Tier
    p_slug = facets_data.get("price_tier")
    if p_slug:
        price_tier = PriceTierFacet.get_by_slug(p_slug, session=db.session)
        if price_tier:
            article.price_tier_id = price_tier.id


def ingest_article_stream(article: Article, data: dict) -> Article | None:
    """
    Update relationships (Topics, Brands, Sources, Facets) for an existing article.
    Does NOT commit; caller should manage the session.
    """
    try:
        _apply_many_to_many(article, data)
        _apply_single_facets(article, data)
        return article
    except Exception:
        logger.exception("[Ingestion] Error merging data into existing article: %s", article.url)
        return None


def store_article(cleaned_data: dict) -> Article | None:
    """
    Create a new Article and link its relationships.
    Commits the transaction on success.
    """
    url = cleaned_data.get("url")
    try:
        section, category = _resolve_taxonomy(cleaned_data)

        article = Article(
            title=cleaned_data.get("title"),
            description=cleaned_data.get("description"),
            content=cleaned_data.get("content"),
            url=url,
            image_url=cleaned_data.get("image_url"),
            published_at=cleaned_data.get("published_at"),
            category_id=category.id,
            section_id=section.id,
            importance_score=cleaned_data.get("importance_score") or 0.0,
            enhanced_query=cleaned_data.get("enhanced_query"),
            is_content_scraped=cleaned_data.get("is_content_scraped", False),
            extra_metadata={}, 
            is_active=True,
        )

        db.session.add(article)
        db.session.flush()
        
        # Link relationships
        if ingest_article_stream(article, cleaned_data):
            db.session.commit()
            return article
        else:
            db.session.rollback()
            return None
            
    except IntegrityError:
        db.session.rollback()
        return Article.query.filter_by(url=url).first()
    except Exception:
        db.session.rollback()
        logger.exception("[Ingestion] Critical error storing new article: %s", url)
        return None

def smart_ingest(raw_data: dict) -> Article | None:
    """
    The universal entry point for all scrapers.
    Encapsulates existence checks, conditional scraping, and storage.
    """
    url = raw_data.get("url")
    if not url:
        return None
        
    article = Article.get_by_url(url, db.session)
    if article:
        if ingest_article_stream(article, raw_data):
            db.session.commit()
            return article
        return None
    
    cleaned = clean_article_data(raw_data, skip_scrape=False)
    if not cleaned:
        return None
        
    return store_article(cleaned)