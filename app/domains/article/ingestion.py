# app/scrapers/storer.py
"""
Stores a cleaned article dict into the Article model.
Orchestrates enrichment via EnrichmentEngine before insertion.
"""
import logging
from sqlalchemy.exc import IntegrityError
from app.core.extensions import db
from .models import Article
from app.domains.system.models import Section, Category, Brand, Topic
from app.integrations.enrichment.engine import EnrichmentEngine

logger = logging.getLogger(__name__)

def store_article(cleaned_data: dict) -> Article | None:
    """
    STRICT TAXONOMY STORAGE:
    1. Deterministic insertion: Uses categorization provided by scraper/query.
    2. URL-based Deduplication with Merging:
       - If URL exists: MERGE new topics and brands into the existing article.
       - If URL is new: Create article and link everything.
    """
    url = (cleaned_data.get("url") or "").strip()
    title = (cleaned_data.get("title") or "").strip()
    
    if not url or not title:
        return None

    try:
        # Resolve Section & Category IDs (Deterministic)
        section_slug = cleaned_data.get("section_slug") or "news"
        section = Section.get_by_slug(section_slug, session=db.session)
        if not section:
            section = Section.get_by_slug("news", session=db.session)

        category_slug = cleaned_data.get("category_slug") or "uncategorized"
        category = Category.get_by_slug(category_slug, session=db.session)
        if not category:
            category = Category.get_by_slug("uncategorized", session=db.session)

        # 1. Deduplication / Merging Logic
        existing_article = Article.query.filter_by(url=url).first()
        if existing_article:
            # MERGE RELATIONSHIPS: Topics
            for t_slug in (cleaned_data.get("topic_slugs") or []):
                topic = Topic.get_by_slug(t_slug, session=db.session)
                if topic:
                    existing_article.add_topic(topic)
            
            # MERGE RELATIONSHIPS: Brands
            for b_slug in (cleaned_data.get("brand_slugs") or []):
                brand = Brand.get_by_slug(b_slug, session=db.session)
                if brand:
                    existing_article.add_brand(brand)

            new_facets = cleaned_data.get("facets") or {}
            existing_facets = existing_article.facets or {}
            # MERGE RELATIONSHIPS: Facets
            for key, value in new_facets.items():
                if isinstance(value, list):
                    existing_values = set(existing_facets.get(key, []))
                    existing_facets[key] = list(existing_values.union(value))
                else:
                    # overwrite if new value exists
                    if value:
                        existing_facets[key] = value

            existing_article.facets = existing_facets
            
            db.session.commit()
            return existing_article

        # 2. CREATE NEW ARTICLE
        article = Article(
            title=title,
            description=cleaned_data.get("description"),
            content=cleaned_data.get("content"),
            url=url,
            image_url=cleaned_data.get("image_url"),
            published_at=cleaned_data.get("published_at"),
            source_name=cleaned_data.get("source_name"),
            category_id=category.id,
            section_id=section.id,
            importance_score=cleaned_data.get("importance_score") or 0.0,
            enhanced_query=cleaned_data.get("enhanced_query"),
            facets=cleaned_data.get("facets") or {},
            is_active=True,
        )
        db.session.add(article)

        # Link Topics (Deterministic)
        for t_slug in (cleaned_data.get("topic_slugs") or []):
            topic = Topic.query.filter_by(slug=t_slug).first()
            if topic:
                article.add_topic(topic)

        # Link Brands (Deterministic)
        for b_slug in (cleaned_data.get("brand_slugs") or []):
            brand = Brand.get_by_slug(b_slug, session=db.session)
            if brand:
                article.add_brand(brand)

        db.session.commit()
        return article

    except IntegrityError:
        db.session.rollback()
        # Final fallback - if a race condition happened, just return the existing one
        return Article.query.filter_by(url=url).first()
    except Exception:
        db.session.rollback()
        logger.exception("[Storer] Critical error in strict storage: %s", url)
        return None
