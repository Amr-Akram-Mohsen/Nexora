# app/integrations/discovery.py
import logging
from typing import Dict, List
from app.shared.utils.slug import generate_slug
from app.shared.constants.taxonomy import TAXONOMY
from app.shared.constants.query_builder import CATEGORY_TOPIC_MAP, QUERY_TEMPLATES

logger = logging.getLogger(__name__)


class DiscoveryManager:
    def __init__(self):
        self.taxonomy = TAXONOMY

    def get_queries_by_section(self, source_filter: str | None = None) -> Dict[str, Dict[str, List[Dict]]]:
        from datetime import datetime
        from app.shared.constants.query_builder import (
            DEFAULT_SOURCE_ALIGNMENT, CATEGORY_SOURCE_OVERRIDES,
            FACET_QUERY_TEMPLATES, QUERY_TEMPLATES, CATEGORY_TOPIC_MAP,
            INTENT_KEYWORDS, SECTION_DEFAULT_INTENTS
        )
        current_year = datetime.now().year
        registry = {}

        sections = self.taxonomy.get("sections", [])
        categories_data = self.taxonomy.get("categories", [])

        logger.info(
            "[INTEGRATION][discovery] start  source_filter=%s  sections=%d  categories=%d",
            source_filter or "(all)",
            len(sections),
            len(categories_data),
        )

        if not sections:
            logger.warning("[INTEGRATION][discovery] no sections found in taxonomy")
        if not categories_data:
            logger.warning("[INTEGRATION][discovery] no categories found in taxonomy")

        for sec in sections:
            sec_slug = generate_slug(sec["name"])
            registry[sec_slug] = {}

            for cat_group in categories_data:
                parent_slug = generate_slug(cat_group["name"])
                
                for child in cat_group.get("children", []):
                    cat_slug = generate_slug(child["name"])
                    if cat_slug == "uncategorized":
                        continue

                    # 1. Determine if this source is allowed for this (Section + Category)
                    allowed_sources = CATEGORY_SOURCE_OVERRIDES.get(parent_slug, {}).get(sec_slug)
                    if allowed_sources is None:
                        allowed_sources = DEFAULT_SOURCE_ALIGNMENT.get(sec_slug, [])

                    if source_filter and source_filter not in allowed_sources:
                        continue

                    # 2. Build Queries based on Source Strength
                    import random
                    from app.shared.constants.query_builder import CATEGORY_BRAND_MAP, RANDOM_QUALIFIERS
                    
                    category_display_name = child["name"]
                    keywords = child.get("search_keywords", [])
                    queries = []

                    # Get primary intent for this section
                    intents = SECTION_DEFAULT_INTENTS.get(sec_slug, ["Review"])
                    
                    # Brand Selection (Layer 1)
                    target_brands = CATEGORY_BRAND_MAP.get(cat_slug, [])
                    selected_brand = random.choice(target_brands) if target_brands else None

                    if source_filter in ["newsapi", "gnews"]:
                        for intent in intents:
                            intent_terms = INTENT_KEYWORDS.get(intent, ["news"])
                            # Standard
                            queries.append({
                                "query": f"{category_display_name} AND {intent_terms[0]}", 
                                "topics": CATEGORY_TOPIC_MAP.get(cat_slug, []), 
                                "brands": [],
                                "intent": intent
                            })
                            # Brand-Specific (if applicable)
                            if selected_brand:
                                queries.append({
                                    "query": f"{selected_brand} AND {intent_terms[0]}", 
                                    "topics": CATEGORY_TOPIC_MAP.get(cat_slug, []), 
                                    "brands": [selected_brand],
                                    "intent": intent
                                })

                    elif source_filter == "youtube":
                        for intent in intents:
                            intent_terms = INTENT_KEYWORDS.get(intent, ["review"])
                            qualifier = random.choice(RANDOM_QUALIFIERS) if sec_slug in ["trends", "reviews"] else ""
                            
                            term = f"{selected_brand} {category_display_name}" if selected_brand else category_display_name
                            q_text = f"{qualifier} {term} {intent_terms[0]}".strip()
                            
                            queries.append({
                                "query": q_text,
                                "topics": CATEGORY_TOPIC_MAP.get(cat_slug, []), 
                                "brands": [selected_brand] if selected_brand else [],
                                "intent": intent
                            })
                            # Year boost version
                            queries.append({
                                "query": f"{term} {intent_terms[0]} {current_year}",
                                "topics": CATEGORY_TOPIC_MAP.get(cat_slug, []), 
                                "brands": [selected_brand] if selected_brand else [],
                                "intent": intent
                            })

                    elif source_filter == "reddit":
                        for intent in intents:
                            term = f"{selected_brand} {category_display_name}" if selected_brand else category_display_name
                            if intent == "Comparison":
                                q_text = f"{term} vs"
                            else:
                                q_text = f"best {term} reddit"
                            
                            queries.append({
                                "query": q_text, 
                                "topics": CATEGORY_TOPIC_MAP.get(cat_slug, []), 
                                "brands": [selected_brand] if selected_brand else [],
                                "intent": intent
                            })

                    else:
                        # Fallback
                        templates = QUERY_TEMPLATES.get(sec_slug, ["{category} news"])
                        for template in templates:
                            q_text = template.format(category=category_display_name, year=current_year)
                            queries.append({
                                "query": q_text, 
                                "topics": CATEGORY_TOPIC_MAP.get(cat_slug, []), 
                                "brands": [],
                                "intent": intents[0] if intents else None
                            })

                    # 3. Facet-Based Query Expansion (Optional Layer)
                    if sec_slug in ["reviews", "tutorials"] and source_filter in ["youtube", "reddit"]:
                        facets_data = self.taxonomy.get("facets", {})
                        for facet_key, options in facets_data.items():
                            if facet_key not in FACET_QUERY_TEMPLATES:
                                continue
                            facet_list = [o for o in options if o.get("category") == cat_group["name"]] if facet_key == "attributes" else options
                            for opt in facet_list[:1]:
                                f_val = opt["name"]
                                for f_template in FACET_QUERY_TEMPLATES[facet_key]:
                                    q_text = f_template.format(category=category_display_name, facet_value=f_val, year=current_year)
                                    queries.append({
                                        "query": q_text, 
                                        "topics": CATEGORY_TOPIC_MAP.get(cat_slug, []), 
                                        "brands": [],
                                        "intent": "Review" if sec_slug == "reviews" else "Tutorial"
                                    })

                    if queries:
                        registry[sec_slug][cat_slug] = queries

        total_queries = sum(
            len(qs)
            for sec_cats in registry.values()
            for qs in sec_cats.values()
        )
        logger.info(
            "[INTEGRATION][discovery] success  source_filter=%s  total_queries=%d  sections_built=%d",
            source_filter or "(all)",
            total_queries,
            len(registry),
        )
        return registry

    def get_section_slugs(self) -> List[str]:
        return [generate_slug(s["name"]) for s in self.taxonomy.get("sections", [])]
