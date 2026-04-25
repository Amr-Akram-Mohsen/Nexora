# app/integrations/discovery.py
from typing import Dict, List
from app.shared.utils.slug import generate_slug
from app.shared.constants.taxonomy import TAXONOMY
from app.shared.constants.query_builder import CATEGORY_TOPIC_MAP, QUERY_TEMPLATES


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
