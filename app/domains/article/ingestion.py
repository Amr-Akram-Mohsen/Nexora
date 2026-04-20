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
        section_slugs = cleaned_data.get("section_slugs") or []
        if not section_slugs and cleaned_data.get("section_slug"):
            section_slugs = [cleaned_data["section_slug"]]
            
        category_slug = cleaned_data.get("category_slug") or "uncategorized"
        category = Category.query.filter_by(slug=category_slug).first()
        if not category:
            category = Category.query.filter_by(slug="uncategorized").first()

        # 1. Deduplication / Merging Logic
        existing_article = Article.query.filter_by(url=url).first()
        if existing_article:
            # MERGE RELATIONSHIPS: Topics
            for t_slug in (cleaned_data.get("topic_slugs") or []):
                topic = Topic.query.filter_by(slug=t_slug).first()
                if topic and topic not in existing_article.topics:
                    existing_article.topics.append(topic)
            
            # MERGE RELATIONSHIPS: Brands
            for b_name in (cleaned_data.get("brand_names") or []):
                brand = Brand.get_or_create(b_name, db.session)
                if brand and brand not in existing_article.brands:
                    existing_article.brands.append(brand)

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
            category_id=category.id if category else None,
            importance_score=cleaned_data.get("importance_score") or 0.0,
            enhanced_query=cleaned_data.get("enhanced_query"),
            is_active=True,
        )
        db.session.add(article)

        # Link Topics (Deterministic)
        for t_slug in (cleaned_data.get("topic_slugs") or []):
            topic = Topic.query.filter_by(slug=t_slug).first()
            if topic:
                article.topics.append(topic)

        # Link Brands (Deterministic)
        for b_name in (cleaned_data.get("brand_names") or []):
            brand = Brand.get_or_create(b_name, db.session)
            if brand:
                article.brands.append(brand)

        # Link Sections (Deterministic)
        for s_slug in section_slugs:
            section = Section.query.filter_by(slug=s_slug).first()
            if section:
                article.sections.append(section)

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
