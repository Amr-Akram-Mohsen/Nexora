from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Dict
from app.shared.constants.query_intelligence import (
    QUERY_TEMPLATES,
    INTENT_KEYWORDS,
    CATEGORY_BRAND_MAP,
    FACET_QUERY_TEMPLATES,
    TEMPORAL_MODIFIERS,
    EXPLORATION_MODIFIERS,
    CATEGORY_SOURCE_SUFFIXES,
    BOOLEAN_SUPPORTED_SOURCES,
    CATEGORY_PROBLEM_MAP,
    FEATURE_MAP,
    SEARCH_KEYWORD_EXPANSIONS,
    CATEGORY_VELOCITY,
)

CURRENT_YEAR = datetime.now().year

# ---------------------------------------------------------------------------
# Deterministic modifier slots
# Each slot is a fixed (temporal, exploration) tuple drawn from the
# cross-product of the modifier lists. The suffix is picked dynamically 
# based on source and category.
# ---------------------------------------------------------------------------

def _build_modifier_slots() -> list[tuple[str, str]]:
    """Pre-compute all (temporal, exploration) combinations."""
    slots: list[tuple[str, str]] = []
    temporals    = [""] + TEMPORAL_MODIFIERS
    explorations = [""] + EXPLORATION_MODIFIERS
    for t in temporals:
        for e in explorations:
            slots.append((t, e))
    return slots


_MODIFIER_SLOTS = _build_modifier_slots()


def _pick_modifiers(position: int, source: str, category_slug: str) -> tuple[str, str, str]:
    """Return a (temporal, exploration, suffix) tuple deterministically from position."""
    t, e = _MODIFIER_SLOTS[position % len(_MODIFIER_SLOTS)]
    
    suffixes = [""]
    if source in CATEGORY_SOURCE_SUFFIXES:
        if category_slug in CATEGORY_SOURCE_SUFFIXES[source]:
            suffixes = CATEGORY_SOURCE_SUFFIXES[source][category_slug]
            
    s = suffixes[position % len(suffixes)]
    return t, e, s


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


# ---------------------------------------------------------------------------
# Per-source query budget constants
# ---------------------------------------------------------------------------

# Maximum expanded_terms to iterate over per (template × intent) combination.
# Boolean sources (event_registry, reddit) support OR-clauses so they get
# more terms per query. Non-boolean sources (youtube, rss) must stay simple.
_MAX_EXPANDED_TERMS: dict[str, int] = {
    "newsapi_ai": 5,
    "youtube": 3,
}

# Maximum intent keyword terms to iterate.
# Boolean sources combine intent terms into one OR-block anyway.
# Non-boolean sources (YouTube, RSS) iterate plain terms separately.
_MAX_INTENT_TERMS: dict[str, int] = {
    "newsapi_ai": 3,
    "youtube": 1,
}


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
    category_query_index: int = 0,
) -> List[Dict]:
    """
    Build rich query variations for a single category+intent+source combination.

    Query count is now tightly bounded per source:
      - Boolean sources (newsapi_ai): OR-block counts as 1 intent
        term but covers multiple signals simultaneously.
      - Non-boolean sources (youtube): limited to 1 intent term and 3
        expanded terms to prevent exponential growth.
    """

    queries = []

    from datetime import datetime, timedelta
    
    velocity = CATEGORY_VELOCITY.get(category_slug, "medium")
    to_date = datetime.utcnow()
    if velocity == "high":
        from_date = to_date - timedelta(days=7)
    elif velocity == "medium":
        from_date = to_date - timedelta(days=30)
    else:
        from_date = to_date - timedelta(days=90)
        
    from_iso = from_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    to_iso = to_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    intent_terms = INTENT_KEYWORDS.get(intent, [intent.lower()])

    templates = QUERY_TEMPLATES.get(section_slug, ["{category}"])

    category_terms = [category_name]
    if selected_brand:
        category_terms.append(selected_brand)
    category_terms.extend(keywords)

    expanded_terms = []
    slug = category_slug.lower()
    expansion = SEARCH_KEYWORD_EXPANSIONS.get(slug)
    is_bool_source = source in BOOLEAN_SUPPORTED_SOURCES

    is_bool_source = source in BOOLEAN_SUPPORTED_SOURCES

    for term in category_terms:
        if expansion and is_bool_source:
            inner = expansion.strip("()")
            expanded_terms.append(f"({term} OR {inner})")
        else:
            expanded_terms.append(term)
            if expansion and not is_bool_source:
                # Non-boolean: add only the first expansion synonym as a
                # separate term. Capped by _MAX_EXPANDED_TERMS anyway.
                first_expansion = expansion.strip("()").split(" OR ")[0]
                expanded_terms.append(first_expansion)

    # FIX: use builtin dict.fromkeys, NOT typing.Dict
    expanded_terms = list(dict.fromkeys(expanded_terms))

    # ── Source-specific caps ────────────────────────────────────────────────
    # These caps are the primary query-count control mechanism.
    max_terms   = _MAX_EXPANDED_TERMS.get(source, 4)
    max_intents = _MAX_INTENT_TERMS.get(source, 2)

    def _safe_query(q_str: str, is_boolean: bool) -> str:
        if is_boolean:
            return q_str
        import re
        while True:
            match = re.search(r"\(([^)]+)\)", q_str)
            if not match:
                break
            options = match.group(1).split(" OR ")
            q_str = q_str.replace(match.group(0), options[0].strip())
        return q_str

    def _sanitize_query(q_str: str, source: str) -> str:
        q_str = q_str.replace("  ", " ")
        tokens = q_str.split()
        seen = set()
        deduped = []
        for t in tokens:
            clean_tl = t.lower().replace("(", "").replace(")", "")
            # Do not deduplicate words that are part of a quoted phrase
            if '"' in t or clean_tl in ["or", "and"] or t in ["(", ")"]:
                deduped.append(t)
            elif clean_tl not in seen:
                seen.add(clean_tl)
                deduped.append(t)
            else:
                # Keep structural parentheses even if the word is dropped
                prefix = "(" * t.count("(")
                suffix = ")" * t.count(")")
                if prefix or suffix:
                    deduped.append(f"{prefix}{suffix}")
        
        q_str = " ".join(deduped)
        q_str = q_str.replace("( ", "(").replace(" )", ")")

        import re
        if source == "newsapi_ai":
            def limit_or_2(m):
                parts = m.group(1).split(" OR ")
                return "(" + " OR ".join(parts[:2]) + ")"
            q_str = re.sub(r"\(([^)]+)\)", limit_or_2, q_str)

        q_str = re.sub(r"\(\s*(?:OR\s+)+", "(", q_str)
        q_str = re.sub(r"(?:\s+OR)+\s*\)", ")", q_str)
        q_str = re.sub(r"\bOR\s+OR\b", "OR", q_str)
        q_str = re.sub(r"\(\s*\)", "", q_str)
        q_str = re.sub(r"^\s*OR\b|\bOR\s*$", "", q_str)
        
        return q_str.replace("  ", " ").strip()

    slot_base = category_query_index  # deterministic starting offset for modifiers

    for t_idx, template in enumerate(templates):
        for e_idx, term in enumerate(expanded_terms[:max_terms]):
            if is_bool_source and len(intent_terms) > 1:
                intent_block = f"({' OR '.join(intent_terms[:3])})"
                process_intent_terms = [intent_block]
            else:
                process_intent_terms = intent_terms[:max_intents]

            for i_idx, intent_term in enumerate(process_intent_terms):
                problems = CATEGORY_PROBLEM_MAP.get(category_slug, ["issue"])
                features = FEATURE_MAP.get(category_slug, ["feature"])
                position = slot_base + t_idx * 100 + e_idx * 10 + i_idx
                problem = problems[position % len(problems)]
                feature = features[position % len(features)]

                raw_query = template.format(
                    category=term,
                    brand=selected_brand or term,
                    year=CURRENT_YEAR,
                    problem=problem,
                    feature=feature,
                )

                if "{category}" not in template:
                    raw_query = f"{term} {raw_query}"

                query = _safe_query(raw_query, is_bool_source)

                query_lower = query.lower()
                intent_words = intent_term.lower().replace("(", "").replace(")", "").split(" or ")
                
                is_redundant = any(word.strip() in query_lower for word in intent_words if len(word.strip()) > 3)
                
                if not is_redundant:
                    query = f"{query} {intent_term}".strip()
                elif is_bool_source and "(" in intent_term and len(intent_words) > 1:
                    pass

                if not is_bool_source:
                    query = _safe_query(query, False)

                temporal, exploration, suffix = _pick_modifiers(position, source, category_slug)

                if source == "youtube":
                    if temporal:
                        query += f" {temporal}"
                else:
                    if temporal:
                        query += f" {temporal}"
                    # Do not add exploration or suffix to news/trends, as it ruins precision.
                    if section_slug not in ["news", "trends"]:
                        if exploration:
                            query += f" {exploration}"
                        if suffix:
                            query += f" {suffix}"

                query = query.replace("  ", " ").strip()
                query = _sanitize_query(query, source)
                if source == "youtube":
                    query = query.replace("review review", "review")

                queries.append(
                    {
                        "query": query.strip(),
                        "topics": topics,
                        "brands": [selected_brand] if selected_brand else [],
                        "intent": intent,
                        "from": from_iso,
                        "to": to_iso,
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

    Only fires for YouTube and Reddit (only sources where facet-style
    "best X for Y" queries yield high-quality discovery results).
    Limited to 1 option per facet key and 1 template per option to prevent
    facet queries from dominating the query pool.
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

        # Reduced from opts[:2] × templates to 1 opt × 1 template.
        # Previously: 3 facet_keys × 2 opts × 2 templates = 12 extra queries per call.
        # Now: 3 facet_keys × 1 opt × 1 template = 3 extra queries per call.
        for opt in options[:1]:
            value = opt["name"]

            # Take only the most specific (first) template per facet key
            template = templates[0]
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
    category_query_index: int = 0,
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
            category_query_index=category_query_index,
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

    return dedupe_queries(all_queries)
