from __future__ import annotations
from pathlib import Path
import json

# Start of the file logic

import random
from datetime import datetime
from typing import List, Dict
from app.shared.constants.query_intelligence import (
    QUERY_TEMPLATES,
    INTENT_KEYWORDS,
    CATEGORY_BRAND_MAP,
    # RANDOM_QUALIFIERS,
    FACET_QUERY_TEMPLATES,
    # SOURCE_DIALECTS,
    TEMPORAL_MODIFIERS,
    EXPLORATION_MODIFIERS,
    QUERY_SUFFIX_ROTATIONS,
    BOOLEAN_SUPPORTED_SOURCES,
    CATEGORY_PROBLEM_MAP,
    FEATURE_MAP,
    SEARCH_KEYWORD_EXPANSIONS,
)

CURRENT_YEAR = datetime.now().year
# the block below is added for debugging queries


DEBUG_QUERY_EXPORT = True


def _debug_export_queries(
    *,
    source: str,
    section_slug: str,
    category_slug: str,
    stage: str,
    queries: List[Dict],
):
    """
    Export generated queries for debugging/inspection.
    """

    if not DEBUG_QUERY_EXPORT:
        return

    debug_dir = Path("instance/debug_queries")
    debug_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{source}_{section_slug}_{category_slug}_{stage}.md"

    filepath = debug_dir / filename

    with open(filepath, "a", encoding="utf-8") as f:
        f.write("\n")
        f.write("=" * 80 + "\n")
        f.write(
            f"{datetime.utcnow().isoformat()} | "
            f"{source} | {section_slug} | {category_slug} | {stage}\n"
        )
        f.write("=" * 80 + "\n\n")

        for idx, q in enumerate(queries, start=1):
            f.write(f"{idx}. {q.get('query', '')}\n")
            f.write(f"   intent: {q.get('intent')}\n")
            f.write(f"   brands: {q.get('brands')}\n")
            f.write(f"   topics: {q.get('topics')}\n")
            f.write("\n")


def dedupe_queries(queries: List[Dict]) -> List[Dict]:
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
) -> List[Dict]:
    """
    Build rich query variations for a single category+intent+source combination.
    """

    queries = []

    intent_terms = INTENT_KEYWORDS.get(intent, [intent.lower()])
    # dialect = SOURCE_DIALECTS.get(source, {})

    source_suffixes = QUERY_SUFFIX_ROTATIONS
    temporal_terms = TEMPORAL_MODIFIERS
    exploration_terms = EXPLORATION_MODIFIERS

    templates = QUERY_TEMPLATES.get(section_slug, ["{category}"])

    category_terms = [category_name]
    category_terms.extend(keywords)

    if selected_brand:
        category_terms.append(selected_brand)

    expanded_terms = []
    slug = category_slug.lower()
    expansion = SEARCH_KEYWORD_EXPANSIONS.get(slug)
    is_bool_source = source in BOOLEAN_SUPPORTED_SOURCES

    for term in category_terms:
        if expansion and is_bool_source:
            # Combine term + expansion: "(Smartphones OR android phone)"
            # Strip outer parens from expansion if they exist to wrap together
            inner = expansion.strip("()")
            expanded_terms.append(f"({term} OR {inner})")
        else:
            expanded_terms.append(term)
            if expansion and not is_bool_source:
                # For non-boolean, just add the first expansion term as a separate query
                # (to maintain some coverage without breaking the search)
                first_expansion = expansion.strip("()").split(" OR ")[0]
                expanded_terms.append(first_expansion)

    expanded_terms = list(Dict.fromkeys(expanded_terms))

    def _safe_query(q_str: str, is_boolean: bool) -> str:
        if is_boolean:
            return q_str
        # Flatten "(A OR B OR C)" -> "A"
        import re

        match = re.search(r"\(([^)]+)\)", q_str)
        if match:
            options = match.group(1).split(" OR ")
            return q_str.replace(match.group(0), options[0].strip())
        return q_str

    for template in templates:
        for term in expanded_terms[:6]:
            # For boolean sources, combine intent terms into one request: (term1 OR term2)
            if is_bool_source and len(intent_terms) > 1:
                intent_block = f"({' OR '.join(intent_terms[:3])})"
                process_intent_terms = [intent_block]
            else:
                process_intent_terms = intent_terms[:2]

            for intent_term in process_intent_terms:
                # Pick a random problem/feature for this query
                problems = CATEGORY_PROBLEM_MAP.get(category_slug, ["issue"])
                features = FEATURE_MAP.get(category_slug, ["feature"])

                raw_query = template.format(
                    category=term,
                    brand=selected_brand or term,
                    year=CURRENT_YEAR,
                    problem=random.choice(problems),
                    feature=random.choice(features),
                )

                if "{category}" not in template:
                    raw_query = f"{term} {raw_query}"

                # Ensure source-safe query logic (strip (OR) if source doesn't support it)
                query = _safe_query(raw_query, is_bool_source)

                # Avoid redundant intent terms
                if intent_term.lower() not in query.lower():
                    query = f"{query} {intent_term}".strip()

                # Cleanup Boolean remnants in intent_term for non-boolean sources
                if not is_bool_source:
                    query = _safe_query(query, False)

                # GNews specific: keep it simple. Only add one modifier at most.
                if source == "gnews":
                    modifier_choice = random.random()
                    if modifier_choice > 0.85 and temporal_terms:
                        query += f" {random.choice(temporal_terms)}"
                    elif modifier_choice > 0.70 and exploration_terms:
                        query += f" {random.choice(exploration_terms)}"
                else:
                    # Standard behavior for YouTube/Reddit (more descriptive)
                    if temporal_terms and random.random() > 0.45:
                        query += f" {random.choice(temporal_terms)}"

                    if exploration_terms and random.random() > 0.65:
                        query += f" {random.choice(exploration_terms)}"

                    if source_suffixes and random.random() > 0.55:
                        query += f" {random.choice(source_suffixes)}"

                # Final cleanup
                query = query.replace("  ", " ").strip()
                if source == "youtube":
                    query = query.replace("review review", "review")

                if source == "reddit":
                    if "reddit" not in query.lower():
                        query += " reddit"

                queries.append(
                    {
                        "query": query.strip(),
                        "topics": topics,
                        "brands": [selected_brand] if selected_brand else [],
                        "intent": intent,
                    }
                )

    return queries


def expand_facet_queries(
    *,
    source: str,
    section_slug: str,
    category_name: str,
    category_group_name: str,
    topics: List[str],
    facets_data: Dict,
) -> List[Dict]:
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
            options = [o for o in options if o.get("category") == category_group_name]

        for opt in options[:2]:
            value = opt["name"]

            for template in templates:
                q = template.format(
                    category=category_name,
                    facet_value=value,
                    year=CURRENT_YEAR,
                )

                results.append(
                    {
                        "query": q,
                        "topics": topics,
                        "brands": [],
                        "intent": "Review",
                    }
                )

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
    facets_data: Dict,
) -> List[Dict]:
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
        # the block below is added for debugging queries
        _debug_export_queries(
            source=source,
            section_slug=section_slug,
            category_slug=category_slug,
            stage=f"intent_{intent.lower()}",
            queries=intent_queries,
        )

    facet_queries = expand_facet_queries(
        source=source,
        section_slug=section_slug,
        category_name=category_name,
        category_group_name=category_group_name,
        topics=topics,
        facets_data=facets_data,
    )

    all_queries.extend(facet_queries)

    # the block below is added for debugging queries
    _debug_export_queries(
        source=source,
        section_slug=section_slug,
        category_slug=category_slug,
        stage="facet_queries",
        queries=facet_queries,
    )
    # random.shuffle(all_queries)

    # the block below is added for debugging queries
    final_queries = dedupe_queries(all_queries)

    _debug_export_queries(
        source=source,
        section_slug=section_slug,
        category_slug=category_slug,
        stage="final_queries",
        queries=final_queries,
    )

    return final_queries

    # return dedupe_queries(all_queries)
