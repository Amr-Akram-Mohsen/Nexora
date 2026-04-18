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

    def get_queries_by_section(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Dynamically generates discovery queries for all sections and leaf categories.
        Structure: { section_slug: { category_slug: [queries] } }
        """
        registry = {}
        sections = self.taxonomy.get("sections", [])
        categories = self.taxonomy.get("categories", [])
        
        # Section mapping (intent modifiers)
        intent_map = {
            "news": ["news", "latest", "update", "announcement"],
            "reviews": ["review", "hands-on", "test", "vs", "comparison"],
            "tutorials": ["tutorial", "how to", "setup guide", "tips"],
            "trends": ["trends 2025", "future", "upcoming"],
            "community": ["reddit", "discussion", "opinion", "thread"]
        }

        for sec in sections:
            sec_slug = generate_slug(sec["name"])
            registry[sec_slug] = {}
            
            for cat in categories:
                # We only search for leaf categories (children)
                for child in cat.get("children", []):
                    cat_slug = generate_slug(child["name"])
                    
                    # Skip uncategorized for discovery
                    if cat_slug == "uncategorized":
                        continue
                        
                    # Build 3-4 diverse queries per category/section
                    modifiers = intent_map.get(sec_slug, ["news"])
                    queries = [
                        f"{child['name']} {modifiers[0]}",
                        f"{cat['name']} {child['name']} {modifiers[1 if len(modifiers) > 1 else 0]}",
                        f"best {child['name']} {sec_slug}" if sec_slug == "reviews" else f"{child['name']} {modifiers[-1]}"
                    ]
                    registry[sec_slug][cat_slug] = queries
                    
        return registry

    def get_section_slugs(self) -> List[str]:
        return [generate_slug(s["name"]) for s in self.taxonomy.get("sections", [])]
