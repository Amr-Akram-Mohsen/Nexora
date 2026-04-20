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

    # NOTE: Extraction logic (keywords, regex, scoring) has been removed 
    # to enforce a deterministic Strict Taxonomy model. 
    # Categories, Sections, Brands, and Topics are now assigned via queries.
