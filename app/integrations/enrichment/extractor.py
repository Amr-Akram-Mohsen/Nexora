import json
import os
import re
from typing import List, Dict, Optional
from app.domains.core.models import Brand, Topic, Category
from app.shared.utils.slug import normalize_name, generate_slug
from app.core.extensions import db

class ExtractorLayer:
    # Class-level cache (Singleton-like behavior)
    _cache = {
        "taxonomy": None,
        "aliases": None,
        "keywords": None
    }

    def __init__(self, session):
        self.session = session
        self._initialize_cache()

    def _initialize_cache(self):
        """Load JSON constants into memory once."""
        if not self._cache["taxonomy"]:
            self._cache["taxonomy"] = self._load_json("app/shared/constants/taxonomy_v2.json")
        if not self._cache["aliases"]:
            self._cache["aliases"] = self._load_json("app/shared/constants/brand_aliases.json")
        if not self._cache["keywords"]:
            self._cache["keywords"] = self._load_json("app/shared/constants/category_keywords.json")

    def _load_json(self, path):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def validate_or_correct_category(self, hint_slug: str, text: str) -> Category:
        """
        Hybrid Validation:
        1. If hint is a valid LEAF -> Accept.
        2. If hint is Top-level/Invalid/Missing -> Fallback to keyword classification.
        3. Always returns a Leaf Category (or Uncategorized).
        """
        text = text.lower()
        
        # 1. Check if hint is a valid leaf
        if hint_slug:
            cat = self.session.query(Category).filter_by(slug=hint_slug, is_leaf=True).first()
            if cat:
                return cat

        # 2. Fallback: Keyword Classification
        keywords_map = self._cache["keywords"] or {}
        for cat_slug, keywords in keywords_map.items():
            if any(kw in text for kw in keywords):
                cat = self.session.query(Category).filter_by(slug=cat_slug, is_leaf=True).first()
                if cat:
                    return cat

        # 3. Last Resort: Uncategorized
        uncat_slug = generate_slug("Uncategorized")
        return self.session.query(Category).filter_by(slug=uncat_slug).first()

    def extract_brands(self, text: str, context_category: Category = None) -> List[Brand]:
        """
        Dynamic extraction with Industry mapping.
        """
        extracted_brands = []
        normalized_text = text.lower()
        
        # Determine industry from context
        industry = "general"
        if context_category:
            # Map category to industry (e.g. smartphones -> mobile)
            # Strategy: use the top-level parent name or a specific mapper
            parent = self.session.query(Category).get(context_category.parent_id) if context_category.parent_id else None
            top_name = parent.name if parent else context_category.name
            
            industry_map = {
                "Electronics": "electronics",
                "Perfumes": "perfumes",
                "Accessories": "fashion",
                "General": "general"
            }
            industry = industry_map.get(top_name, "general")

        # Step 1: Alias matching (Highest precision)
        aliases = self._cache["aliases"] or {}
        for brand_name, alias_list in aliases.items():
            for alias in alias_list:
                if alias.lower() in normalized_text:
                    brand = Brand.get_or_create(brand_name, self.session, industry)
                    if brand not in extracted_brands:
                        extracted_brands.append(brand)
                    break
        
        # Step 2: Direct lookup for existing brands
        # Only if we didn't find them via aliases already
        # (This handles brands that don't have aliases)
        # Note: We limit this to active brands to avoid false positives
        
        return extracted_brands

    def detect_topics(self, text: str) -> List[Topic]:
        detected_topics = []
        normalized_text = text.lower()
        
        # Topic rules (can be moved to JSON later if needed)
        intent_rules = {
            generate_slug("Buying Guides"):  ["guide", "how to buy", "best way to"],
            generate_slug("Top 10 Lists"):   ["top 10", "best of", "comparison"],
            generate_slug("Budget Picks"):   ["cheap", "budget", "affordable", "value"],
            generate_slug("Premium Luxury"): ["premium", "luxury", "high-end", "expensive"]
        }
        
        for slug, keywords in intent_rules.items():
            if any(kw in normalized_text for kw in keywords):
                topic = self.session.query(Topic).filter_by(slug=slug).first()
                if topic and topic not in detected_topics:
                    detected_topics.append(topic)
                    
        return detected_topics
