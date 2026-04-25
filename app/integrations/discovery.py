# app/integrations/discovery.py
from typing import Dict, List
from app.shared.utils.slug import generate_slug
from app.shared.constants.taxonomy import TAXONOMY


CATEGORY_TOPIC_MAP = {
    # Electronics
    "smartphones": ["travel-gear"],   # used on the go
    "laptops": ["home-office"],
    "tablets": ["home-office"],
    "smartwatches": ["fitness"],
    "earbuds": ["fitness"],
    "headphones": ["home-office"],
    "cameras": ["photography"],

    # Perfumes
    "niche-artisanal": [],
    "oud-oriental": [],

    # Accessories
    "watches": ["fitness"],            # smart watches overlap
    "bags": ["travel-gear"],
    "sunglasses": ["travel-gear"],
    "jewelry": [],
}


QUERY_TEMPLATES = {
    "news": [
        "{category} news",
        "{category} launch",
        "{category} announcement",
        "new {category} release",
    ],
    "reviews": [
        "{category} review OR hands-on",
        "best {category} {year}",
        "{category} test OR impressions",
        "{category} full review",
    ],
    "tutorials": [
        "how to use {category}",
        "{category} guide",
        "{category} tips and tricks",
    ],
    "trends": [
        "{category} trends {year}",
        "future of {category}",
        "{category} upcoming releases",
    ],
    "community": [
        "{category} discussion",
        "{category} user opinions",
    ],
}


class DiscoveryManager:
    def __init__(self):
        self.taxonomy = TAXONOMY

    def get_queries_by_section(self) -> Dict[str, Dict[str, List[Dict]]]:
        from datetime import datetime
        current_year = datetime.now().year
        registry = {}

        sections = self.taxonomy.get("sections", [])
        categories_data = self.taxonomy.get("categories", [])

        for sec in sections:
            sec_slug = generate_slug(sec["name"])
            registry[sec_slug] = {}

            for cat in categories_data:
                for child in cat.get("children", []):
                    cat_slug = generate_slug(child["name"])

                    if cat_slug == "uncategorized":
                        continue

                    templates = QUERY_TEMPLATES.get(sec_slug, ["{category} news"])

                    queries = []
                    for template in templates:
                        # Inject category and current year
                        q_text = template.format(category=child["name"], year=current_year)
                        queries.append({
                            "query": q_text,
                            "topics": CATEGORY_TOPIC_MAP.get(cat_slug, []),
                            "brands": []
                        })

                    registry[sec_slug][cat_slug] = queries

        return registry

    def get_section_slugs(self) -> List[str]:
        return [generate_slug(s["name"]) for s in self.taxonomy.get("sections", [])]
