# app/integrations/enrichment/engine.py
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
        STRICT TAXONOMY ENGINE:
        No inference. Returns the categorization provided by the scraper.
        """
        return {
            "category": article_data.get("category_slug") or "uncategorized",
            "section_slug": article_data.get("section_slug") or "news",
            "topic_slugs": article_data.get("topic_slugs") or [],
            "brand_slugs": article_data.get("brand_slugs") or [],
            "importance_score": article_data.get("importance_score") or 0.5,
            "enhanced_query": article_data.get("enhanced_query") or ""
        }
