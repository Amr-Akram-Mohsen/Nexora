import logging
from .extractor import ExtractorLayer
from .scorer import ScoringLayer
from .query_builder import QueryBuilderLayer
from app.core.extensions import db

logger = logging.getLogger(__name__)

class EnrichmentEngine:
    def __init__(self, session=None):
        self.session = session or db.session
        self.extractor = ExtractorLayer(self.session)
        self.scorer = ScoringLayer()
        self.query_builder = QueryBuilderLayer()

    def process_article(self, article_data: dict) -> dict:
        """
        Main entry point for article enrichment.
        Flow: Validate Category -> Extract Brands -> Detect Topics -> Score -> Build Query.
        """
        title = article_data.get("title", "")
        description = article_data.get("description", "")
        content = article_data.get("content") or ""
        full_text = f"{title} {description} {content}"

        # 1. Validate / Correct Category (Hybrid)
        category = self.extractor.validate_or_correct_category(
            article_data.get("category_slug"), 
            full_text
        )

        # 2. Section Handling (Fallback to News)
        section_slug = article_data.get("section_slug")
        if not section_slug:
            # Try to detect from title
            if "review" in title.lower():
                section_slug = "reviews"
            elif "tutorial" in title.lower() or "how to" in title.lower():
                section_slug = "tutorials"
            else:
                section_slug = "news"

        # 3. Dynamic Extraction
        brands = self.extractor.extract_brands(full_text, category)
        topics = self.extractor.detect_topics(full_text)

        # 4. Scoring
        importance_score = self.scorer.calculate_importance(
            article_data.get("source_name", ""),
            brands,
            full_text,
            article_data.get("published_at")
        )

        # 5. Enhanced Query Building
        enhanced_query = self.query_builder.build_enhanced_query(
            title, 
            category, 
            brands, 
            topics
        )

        return {
            "category": category.slug if category else "uncategorized",
            "sections": [section_slug],
            "brands": [{"name": b.name, "industry": b.industry} for b in brands],
            "topics": [t.slug for t in topics],
            "importance_score": importance_score,
            "enhanced_query": enhanced_query
        }

    def enrich_and_store(self, cleaned_data: dict):
        """Processes and returns raw objects for DB insertion."""
        # This helper returns the actual model objects if needed, 
        # but the request asks for structured JSON output.
        return self.process_article(cleaned_data)
