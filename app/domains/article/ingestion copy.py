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
        from app.shared.utils.slug import generate_slug
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


def ingest_article_stream(raw_data: dict) -> Article | None:
    """
    High-level orchestrator for raw article data from scrapers.
    1. Checks if article exists (deduplication).
    2. If exists: MERGES relationships (topics, brands, sources) from raw data.
    3. If new: Cleans/Scrapes the article and creates a new record.
    """
    url = (raw_data.get("url") or "").strip()
    if not url:
        return None

    try:
        # 1. Deduplication Check
        
        existing_article = Article.query.filter_by(url=url).first()
        if existing_article:
            # Merging logic: Update relationships without re-scraping
            _apply_many_to_many(existing_article, raw_data)
            _apply_single_facets(existing_article, raw_data)
            db.session.commit()
            return existing_article

        # 2. It's New: Full cleaning and scraping
        cleaned = clean_article_data(raw_data, skip_scrape=False)
        if not cleaned:
            return None

        # 3. Resolve Taxonomy
        section, category = _resolve_taxonomy(cleaned)

        # 4. Create New Article
        article = Article(
            title=cleaned.get("title"),
            description=cleaned.get("description"),
            content=cleaned.get("content"),
            url=url,
            image_url=cleaned.get("image_url"),
            published_at=cleaned.get("published_at"),
            category_id=category.id,
            section_id=section.id,
            importance_score=cleaned.get("importance_score") or 0.0,
            enhanced_query=cleaned.get("enhanced_query"),
            metadata={},  # metadata starts empty as requested
            is_active=True,
        )
        
        # Apply all relationships
        _apply_many_to_many(article, cleaned)
        _apply_single_facets(article, cleaned)
        
        db.session.add(article)
        db.session.commit()
        return article

    except IntegrityError:
        db.session.rollback()
        return Article.query.filter_by(url=url).first()
    except Exception:
        db.session.rollback()
        logger.exception("[Ingestion] Critical error in stream: %s", url)
        return None

# Deprecated: alias for backward compatibility until scrapers are updated
def store_article(cleaned_data: dict) -> Article | None:
    return ingest_article_stream(cleaned_data)
