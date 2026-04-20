import json
import os
from typing import Dict, List
from app.shared.utils.slug import generate_slug

TAXONOMY_PATH = "app/shared/constants/taxonomy_v2.json"

class DiscoveryManager:
    def __init__(self):
        self.taxonomy = self._load_json(TAXONOMY_PATH)
        
    def _load_json(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_queries_by_section(self) -> Dict[str, Dict[str, List[Dict]]]:
        """
        Dynamically generates discovery queries for all sections and leaf categories.
        Structure: { section_slug: { category_slug: [ {query, topics, brands} ] } }
        """
        registry = {}
        sections = self.taxonomy.get("sections", [])
        categories_data = self.taxonomy.get("categories", [])
        
        # Section mapping (intent modifiers)
        intent_map = {
            "news": ["news", "latest", "update"],
            "reviews": ["review", "test", "comparison"],
            "tutorials": ["tutorial", "how to", "guide"],
            "trends": ["trends 2025", "upcoming"],
            "community": ["discussion", "opinion"]
        }

        for sec in sections:
            sec_slug = generate_slug(sec["name"])
            registry[sec_slug] = {}
            
            for cat in categories_data:
                # We only search for leaf categories
                for child in cat.get("children", []):
                    cat_slug = generate_slug(child["name"])
                    if cat_slug == "uncategorized": continue
                        
                    modifiers = intent_map.get(sec_slug, ["news"])
                    
                    # Deterministic Metadata
                    # Topic: Map category to a primary topic if possible
                    topic_mapping = {
                        "smartphones": ["mobile-tech"],
                        "laptops": ["computing"],
                        "smartwatches": ["wearables"],
                        "headphones": ["audio"],
                        "earbuds": ["audio"],
                        "perfumes": ["fragrances"],
                        "watches": ["luxury-watches"],
                        "bags": ["fashion-accessories"]
                    }
                    
                    # Brand: Derive primary brand from query keywords for high precision
                    # or leave empty for generic category searches
                    
                    category_queries = []
                    
                    # Query 1: Generic category news
                    category_queries.append({
                        "query": f"{child['name']} {modifiers[0]}",
                        "topics": topic_mapping.get(cat_slug, []),
                        "brands": []
                    })
                    
                    # Query 2: Specific High-Volume Query
                    category_queries.append({
                        "query": f"best {child['name']} 2025",
                        "topics": topic_mapping.get(cat_slug, []) + ["buying-guides"],
                        "brands": []
                    })

                    registry[sec_slug][cat_slug] = category_queries
                    
        return registry

    def get_section_slugs(self) -> List[str]:
        return [generate_slug(s["name"]) for s in self.taxonomy.get("sections", [])]
