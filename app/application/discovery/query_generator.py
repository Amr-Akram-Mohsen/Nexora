from __future__ import annotations

import random
from datetime import datetime
from typing import Dict, List

from app.shared.constants.query_intelligence import (
    QUERY_TEMPLATES,
    INTENT_KEYWORDS,
    CATEGORY_BRAND_MAP,
    RANDOM_QUALIFIERS,
    FACET_QUERY_TEMPLATES,
    SOURCE_DIALECTS,
    TEMPORAL_MODIFIERS,
    EXPLORATION_MODIFIERS,
    SEARCH_KEYWORD_EXPANSIONS,
    QUERY_SUFFIX_ROTATIONS,
)

CURRENT_YEAR = datetime.now().year


def dedupe_queries(queries: List[dict]) -> List[dict]:
    """
    Remove duplicate queries while preserving order.
    """
    seen = set()
    final = []

    for q in queries:
        normalized = q["query"].strip().lower()

        if normalized in seen:
            continue

        seen.add(normalized)
        final.append(q)

    return final


def build_query_variants(
    *,
    source: str,
    section_slug: str,
    category_name: str,
    category_slug: str,
    keywords: List[str],
    intent: str,
    selected_brand: str | None,
    topics: List[str],
) -> List[dict]:
    """
    Build rich query variations for a single category+intent+source combination.
    """

    queries = []

    intent_terms = INTENT_KEYWORDS.get(intent, [intent.lower()])
    dialect = SOURCE_DIALECTS.get(source, {})

    source_suffixes = QUERY_SUFFIX_ROTATIONS
    temporal_terms = TEMPORAL_MODIFIERS
    exploration_terms = EXPLORATION_MODIFIERS

    templates = QUERY_TEMPLATES.get(section_slug, ["{category}"])

    category_terms = [category_name]
    category_terms.extend(keywords)

    if selected_brand:
        category_terms.append(selected_brand)

    expanded_terms = []

    for term in category_terms:
        expanded_terms.append(term)

        slug = category_slug.lower()
        expanded_terms.extend(
            SEARCH_KEYWORD_EXPANSIONS.get(slug, [])
        )

    expanded_terms = list(dict.fromkeys(expanded_terms))

    for template in templates:

        for term in expanded_terms[:6]:

            for intent_term in intent_terms[:2]:

                query = template.format(
                    category=term,
                    brand=selected_brand or term,
                    year=CURRENT_YEAR,
                )

                if "{category}" not in template:
                    query = f"{term} {query}"

                query = f"{query} {intent_term}".strip()

                if selected_brand and selected_brand.lower() not in query.lower():
                    if random.random() > 0.55:
                        query = f"{selected_brand} {query}"

                if temporal_terms and random.random() > 0.45:
                    query += f" {random.choice(temporal_terms)}"

                if exploration_terms and random.random() > 0.65:
                    query += f" {random.choice(exploration_terms)}"

                if source_suffixes and random.random() > 0.55:
                    query += f" {random.choice(source_suffixes)}"

                if source == "youtube":
                    query = query.replace("review review", "review")

                if source == "reddit":
                    if "reddit" not in query.lower():
                        query += " reddit"

                queries.append({
                    "query": query.strip(),
                    "topics": topics,
                    "brands": [selected_brand] if selected_brand else [],
                    "intent": intent,
                })

    return queries


def expand_facet_queries(
    *,
    source: str,
    section_slug: str,
    category_name: str,
    category_group_name: str,
    topics: List[str],
    facets_data: dict,
) -> List[dict]:
    """
    Generate facet-driven discovery queries.
    """

    if source not in ["youtube", "reddit"]:
        return []

    if section_slug not in ["reviews", "tutorials", "trends"]:
        return []

    results = []

    for facet_key, templates in FACET_QUERY_TEMPLATES.items():

        options = facets_data.get(facet_key, [])

        if facet_key == "attributes":
            options = [
                o for o in options
                if o.get("category") == category_group_name
            ]

        for opt in options[:2]:

            value = opt["name"]

            for template in templates:

                q = template.format(
                    category=category_name,
                    facet_value=value,
                    year=CURRENT_YEAR,
                )

                results.append({
                    "query": q,
                    "topics": topics,
                    "brands": [],
                    "intent": "Review",
                })

    return results


def generate_discovery_queries(
    *,
    source: str,
    section_slug: str,
    category_name: str,
    category_slug: str,
    category_group_name: str,
    keywords: List[str],
    intents: List[str],
    topics: List[str],
    facets_data: dict,
) -> List[dict]:
    """
    Main high-level query generation pipeline.
    """

    all_queries = []

    target_brands = CATEGORY_BRAND_MAP.get(category_slug, [])

    selected_brand = None

    if target_brands:
        from app.shared.utils.rotation_state import RotationState

        rotator = RotationState("discovery_brands")

        selected_brand = rotator.get_next(
            category_slug,
            target_brands,
        )

    for intent in intents:

        intent_queries = build_query_variants(
            source=source,
            section_slug=section_slug,
            category_name=category_name,
            category_slug=category_slug,
            keywords=keywords,
            intent=intent,
            selected_brand=selected_brand,
            topics=topics,
        )

        all_queries.extend(intent_queries)

    facet_queries = expand_facet_queries(
        source=source,
        section_slug=section_slug,
        category_name=category_name,
        category_group_name=category_group_name,
        topics=topics,
        facets_data=facets_data,
    )

    all_queries.extend(facet_queries)

    # random.shuffle(all_queries)

    return dedupe_queries(all_queries)