from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Brand detection
# ---------------------------------------------------------------------------

def detect_brands(text: str, brands_list: list[dict]) -> list[str]:
    """
    Detect brands in text using the taxonomy brand data (name + aliases).

    Strategy:
      1. Exact word-boundary match for each brand name and its aliases.
      2. Returns canonical brand names (deduplicated, order-preserving).

    Args:
        text: The combined title + description to search in.
        brands_list: List of brand dicts from taxonomy, each with
                     ``name`` (str) and optional ``aliases`` (list[str]).

    Returns:
        List of canonical brand names detected.
    """
    if not text:
        return []

    text_lower = text.lower()
    detected: list[str] = []
    seen: set[str] = set()

    for brand_data in brands_list:
        brand_name = brand_data.get("name", "")
        if not brand_name:
            continue
        aliases = brand_data.get("aliases", [])

        # Patterns: canonical name first (highest confidence), then aliases
        patterns = [brand_name] + list(aliases)

        for p in patterns:
            if not p:
                continue
            try:
                if re.search(rf"\b{re.escape(p.lower())}\b", text_lower):
                    if brand_name not in seen:
                        detected.append(brand_name)
                        seen.add(brand_name)
                    break  # Already matched this brand — don't double-count
            except re.error:
                continue

    return detected


# ---------------------------------------------------------------------------
# Category-brand relationship (used during enrichment to infer category hints)
# ---------------------------------------------------------------------------

def brands_to_category_hints(detected_brands: list[str]) -> list[str]:
    """
    Given a list of detected brand names, return category slug hints derived
    from the CATEGORY_BRAND_MAP.

    Used as a secondary signal when query-context category is absent or weak.
    Imported lazily to avoid circular imports.
    """
    from app.shared.constants.query_intelligence import CATEGORY_BRAND_MAP

    # Build an inverted map: brand_name (lowercase) → [category_slug, ...]
    brand_to_cats: dict[str, list[str]] = {}
    for cat_slug, brands in CATEGORY_BRAND_MAP.items():
        for b in brands:
            key = b.lower()
            brand_to_cats.setdefault(key, []).append(cat_slug)

    hints: list[str] = []
    seen_cats: set[str] = set()
    for brand in detected_brands:
        cats = brand_to_cats.get(brand.lower(), [])
        for cat in cats:
            if cat not in seen_cats:
                hints.append(cat)
                seen_cats.add(cat)
    return hints
