# app/scrapers/storer.py
"""
Stores a cleaned article dict into the Article model.
Orchestrates enrichment via EnrichmentEngine before insertion.
"""
import logging
from sqlalchemy.exc import IntegrityError
from app.core.extensions import db
from .models import Article
from app.domains.core.models import Section, Category, Brand, Topic
from app.integrations.enrichment.engine import EnrichmentEngine

logger = logging.getLogger(__name__)

def store_article(cleaned_data: dict) -> Article | None:
    """
    Store one cleaned article.
    Flow: Cleaned Data -> Enrichment Engine -> Article Object -> Database.
    """
    url = (cleaned_data.get("url") or "").strip()
    title = (cleaned_data.get("title") or "").strip()
    source_name = (cleaned_data.get("source_name") or "").strip()

    if not url or not title:
        return None

    try:
        # 1. Deduplication check
        if Article.query.filter_by(url=url).first():
            return None
            
        if source_name and Article.query.filter_by(source_name=source_name, title=title).first():
            return None

        # 2. Enrichment
        engine = EnrichmentEngine(db.session)
        enriched = engine.process_article(cleaned_data)

        # 3. Resolve Category (Leaf only ensured by engine)
        category_slug = enriched["category"]
        category = Category.query.filter_by(slug=category_slug).first()
        if not category:
            # Fallback to Uncategorized if seed is missing
            category = Category.query.filter_by(slug="uncategorized").first()

        # 4. Create Article
        article = Article(
            title=title,
            description=cleaned_data.get("description"),
            content=cleaned_data.get("content"),
            url=url,
            image_url=cleaned_data.get("image_url"),
            published_at=cleaned_data.get("published_at"),
            source_name=source_name,
            category_id=category.id if category else None,
            importance_score=enriched["importance_score"],
            enhanced_query=enriched["enhanced_query"],
            is_active=True,
        )
        db.session.add(article)

        # 4. Resolve M2M: Sections
        for sec_slug in enriched["sections"]:
            section = Section.query.filter_by(slug=sec_slug).first()
            if section:
                article.sections.append(section)

        # 5. Resolve M2M: Brands (Deterministic lookup)
        for brand_info in enriched["brands"]:
            # Use Brand.get_or_create which handles normalization
            brand = Brand.get_or_create(brand_info["name"], db.session)
            if brand:
                # Update industry if it was 'general' and we have better context now
                if (not brand.industry or brand.industry == "general") and brand_info["industry"] != "general":
                    brand.industry = brand_info["industry"]
                article.brands.append(brand)

        # 6. Resolve M2M: Topics
        for topic_slug in enriched["topics"]:
            topic = Topic.query.filter_by(slug=topic_slug).first()
            if topic:
                article.topics.append(topic)

        db.session.commit()
        return article

    except IntegrityError:
        db.session.rollback()
        return None
    except Exception:
        db.session.rollback()
        logger.exception("[Storer] Error storing article: %s", url)
        return None
