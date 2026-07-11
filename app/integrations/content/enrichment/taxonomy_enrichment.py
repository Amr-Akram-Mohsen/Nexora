"""
app/integrations/content/enrichment/taxonomy_enrichment.py
-----------------------------------------------------------
Taxonomy Enrichment Engine
--------------------------
A deterministic, scoring-based taxonomy assignment step that runs
**after** discovery/normalization and **before** persistence.

Responsibilities
~~~~~~~~~~~~~~~~
* Re-evaluate category assignment using content signals (title, description,
  source tags, source categories, discovery metadata).
* Enrich topic_slugs, brand_slugs, and facets (intent, gender, attributes)
  with confidence-weighted matching against the full Nexora taxonomy.

Design Principles
~~~~~~~~~~~~~~~~~
* No AI / LLM / embedding / external services.
* Fully deterministic — same input always produces the same output.
* Transparent — every decision carries an explanatory score breakdown.
* Non-destructive — only replaces assignments when the enriched score
  clearly beats the discovery-assigned one (confidence threshold).

Scoring Strategy
~~~~~~~~~~~~~~~~
Category Re-assignment
  - Keyword match score : each taxonomy keyword / alias found in the
    content signals contributes a weighted point.
  - Title signal weight : 3×   (strongest signal for primary category)
  - Description weight  : 2×
  - Source tag weight   : 1×
  - Source category     : 2×   (external metadata is authoritative)
  - Candidate must beat the discovery-assigned category by at least
    CATEGORY_CONFIDENCE_THRESHOLD points to trigger re-assignment.

Topic Enrichment
  - Removed

Brand Enrichment
  - Removed

Attribute Enrichment
  - Extends facets["attributes"] using the existing facet_detector logic,
    now correctly scoped to the *enriched* category rather than the
    discovery-assigned one.

Intent / Gender Facets
  - Re-runs intent/gender detection using enriched category context when
    the discovery-assigned category differs from the enriched one.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.shared.constants.taxonomy import TAXONOMY
from app.shared.dto.ingestion import EnrichedItemDTO

logger = logging.getLogger(__name__)

_NAME = "taxonomy_enrichment"

# ---------------------------------------------------------------------------
# Confidence thresholds
# ---------------------------------------------------------------------------

# A candidate category must exceed the discovery-assigned score by at least
# this many points before we override the assignment.
CATEGORY_CONFIDENCE_THRESHOLD = 4

# Minimum cumulative score for an attribute to be appended.
ATTRIBUTE_MIN_SCORE = 1

# ---------------------------------------------------------------------------
# Signal weights
# ---------------------------------------------------------------------------

SIGNAL_WEIGHT = {
    "title": 3,
    "description": 2,
    "source_category": 2,
    "source_tag": 1,
}


# ---------------------------------------------------------------------------
# Static keyword maps (derived from taxonomy + domain knowledge)
# ---------------------------------------------------------------------------

# Maps leaf category slug → signal keywords (beyond what TAXONOMY already holds)
# Used for disambiguation: "smartphone camera" should score higher for
# "smartphones" than for "cameras".
CATEGORY_DISAMBIGUATION_KEYWORDS: dict[str, list[str]] = {
    "smartphones": [
        "smartphone", "mobile phone", "android phone", "iphone",
        "cell phone", "flagship phone", "camera phone",
        "galaxy s", "pixel phone", "best smartphone",
        "phone review", "phone camera",          # key disambiguation signals
        "phone spec", "mobile spec",
    ],
    "laptops": [
        "laptop", "notebook", "ultrabook", "macbook", "gaming laptop",
        "creator laptop", "laptop review", "laptop deal",
    ],
    "tablets": [
        "tablet", "ipad", "android tablet", "drawing tablet",
        "surface pro", "tablet review",
    ],
    "cameras": [
        "camera", "mirrorless", "dslr", "photography gear",
        "lens review", "camera sensor", "vlogging camera",
        "action cam", "photo camera",
        # exclude common phone-camera phrases by NOT including "phone camera"
        # (the phrase itself is neutral; context of surrounding words matters)
    ],
    "smartwatches": [
        "smartwatch", "smart watch", "fitness tracker", "apple watch",
        "galaxy watch", "wearable", "health tracking",
    ],
    "earbuds": [
        "earbuds", "true wireless", "tws", "airpods", "in-ear",
        "wireless earbuds",
    ],
    "headphones": [
        "headphones", "over-ear", "headset", "hi-fi", "noise cancelling headphone",
    ],
    "niche-artisanal": [
        "niche fragrance", "artisan perfume", "indie scent", "niche perfume",
        "small batch", "artisanal fragrance",
    ],
    "oud-oriental": [
        "oud", "arabic perfume", "oriental perfume", "attar", "bakhoor",
        "middle eastern fragrance",
    ],
    "watches": [
        "luxury watch", "mechanical watch", "automatic watch", "chronograph",
        "dive watch", "dress watch", "horology", "timepiece",
    ],
    "bags": [
        "handbag", "backpack", "leather bag", "luxury bag", "tote bag",
        "everyday carry bag", "laptop bag",
    ],
    "sunglasses": [
        "sunglasses", "eyewear", "shades", "polarized lens",
        "designer sunglasses", "uv protection glasses",
    ],
    "jewelry": [
        "jewelry", "jewellery", "necklace", "bracelet", "ring", "earring",
        "fine jewelry", "gold jewelry",
    ],
}

# Maps attribute slug → signal keywords (subset of facet_detector logic,
# moved here so enrichment can apply them with the *corrected* category).
ATTRIBUTE_KEYWORD_MAP: dict[str, list[str]] = {
    "noise-cancelling": [
        "noise cancelling", "noise canceling", "anc", "active noise",
    ],
    "waterproof": [
        "waterproof", "water resistant", "ipx", "ip68", "ip67", "ip65",
    ],
    "battery-life": [
        "battery life", "long battery", "all day battery", "endurance",
    ],
    "wireless": [
        "wireless", "bluetooth",
    ],
    "fast-charging": [
        "fast charging", "quick charge", "rapid charge", "65w", "120w",
        "supervooc", "warp charge",
    ],
    "lightweight": [
        "lightweight", "light weight", "thin and light", "compact",
    ],
    "gaming": [
        "gaming", "game mode", "120hz", "144hz", "refresh rate",
    ],
    "ai-features": [
        "ai camera", "ai feature", "on-device ai", "generative ai",
        "machine learning", "neural engine",
    ],
    "long-lasting": [
        "long lasting", "longevity", "beast mode", "all day", "long-lasting",
        "sillage",
    ],
    "woody": [
        "woody", "wood", "sandalwood", "cedar", "vetiver",
    ],
    "floral": [
        "floral", "rose", "jasmine", "flower", "peony", "iris",
    ],
    "citrus": [
        "citrus", "lemon", "orange", "bergamot", "lime", "grapefruit",
    ],
}

# Facets that are gender-relevant by enriched category
GENDER_RELEVANT_ENRICHED_CATEGORIES = {
    "niche-artisanal", "oud-oriental", "watches", "bags", "sunglasses", "jewelry",
}

# Intent keyword patterns (mirrors facet_detector but normalized as a map)
INTENT_PATTERN_MAP: dict[str, list[str]] = {
    "first-impressions": [
        "hands-on", "hands on", "first look", "first impressions",
    ],
    "unboxing": ["unboxing"],
    "review": [
        "review", "real-world test", "long term",
    ],
    "top-list": [
        "best ", "top 5", "top 10", "buying guide",
    ],
    "comparison": [
        " vs ", " versus ", "comparison",
    ],
    "tutorial": [
        "how to", "setup guide", "tutorial", "tips",
    ],
    "news": [
        "announced", "launch", "release", "unveiled",
    ],
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _text_lower(text: str | None) -> str:
    return (text or "").lower()


def _keyword_score(text: str, keywords: list[str]) -> int:
    """Return how many keywords from *keywords* appear in *text*."""
    count = 0
    for kw in keywords:
        if re.search(r"\b" + re.escape(kw.lower()) + r"\b", text):
            count += 1
    return count


def _build_category_keyword_pool() -> dict[str, list[str]]:
    """
    Merge CATEGORY_DISAMBIGUATION_KEYWORDS with taxonomy search_keywords
    to produce a rich per-category keyword pool.
    """
    pool: dict[str, list[str]] = {}

    for cat_group in TAXONOMY.get("categories", []):
        for child in cat_group.get("children", []):
            slug = child["name"].lower().replace(" ", "-").replace("&", "-").replace(" & ", "-")
            # normalize multi-hyphen
            while "--" in slug:
                slug = slug.replace("--", "-")
            kws = [k.lower() for k in child.get("search_keywords", [])]
            extra = [k.lower() for k in CATEGORY_DISAMBIGUATION_KEYWORDS.get(slug, [])]
            pool[slug] = list(dict.fromkeys(kws + extra))  # preserve order, dedup

    # Also include disambiguation-only slugs not in TAXONOMY children
    for slug, kws in CATEGORY_DISAMBIGUATION_KEYWORDS.items():
        if slug not in pool:
            pool[slug] = [k.lower() for k in kws]

    return pool


_CATEGORY_KEYWORD_POOL: dict[str, list[str]] = _build_category_keyword_pool()


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------


def _score_category_against_signals(
    candidate_slug: str,
    title: str,
    description: str,
    source_tags: list[str],
    source_categories: list[str],
) -> int:
    """
    Compute a weighted score for how strongly *candidate_slug* matches
    the provided content signals.

    Returns an integer score (higher = stronger match).
    """
    keywords = _CATEGORY_KEYWORD_POOL.get(candidate_slug, [])
    if not keywords:
        return 0

    score = 0
    score += _keyword_score(title, keywords) * SIGNAL_WEIGHT["title"]
    score += _keyword_score(description, keywords) * SIGNAL_WEIGHT["description"]

    tag_blob = " ".join(source_tags).lower()
    cat_blob = " ".join(source_categories).lower()

    score += _keyword_score(tag_blob, keywords) * SIGNAL_WEIGHT["source_tag"]
    score += _keyword_score(cat_blob, keywords) * SIGNAL_WEIGHT["source_category"]

    return score


# ---------------------------------------------------------------------------
# Public enrichment function
# ---------------------------------------------------------------------------


def enrich_taxonomy(product: EnrichedItemDTO | dict) -> EnrichedItemDTO:
    """
    Taxonomy Enrichment step.

    Accepts an ``EnrichedItemDTO`` (or a plain dict) that has already been
    through classification and normalization, and returns an updated
    ``EnrichedItemDTO`` with refined taxonomy assignments.

    This function is **pure** — it does not touch the database and performs
    no network calls.  All decisions are driven by keyword matching against
    the in-process TAXONOMY constant.

    Parameters
    ----------
    product:
        The normalized+classified content product.

    Returns
    -------
    EnrichedItemDTO
        A new DTO with potentially updated:
        * ``category_slug``
        * ``facets``  (intent, gender, attributes)
    """
    data: dict = product.model_dump() if hasattr(product, "model_dump") else dict(product)

    title_raw: str = data.get("title") or ""
    description_raw: str = data.get("description") or ""
    title = _text_lower(title_raw)
    description = _text_lower(description_raw)

    # --- Source metadata from the raw product (may be None) ---
    source_tags: list[str] = data.get("source_tags") or []
    source_categories: list[str] = data.get("source_categories") or []

    discovery_category: str = data.get("category_slug") or ""

    logger.debug(
        "[%s] start  title='%.60s'  discovery_category=%s",
        _NAME,
        title_raw,
        discovery_category,
    )

    # ── 1. Category Re-assignment ─────────────────────────────────────────
    enriched_category = _enrich_category(
        discovery_category=discovery_category,
        title=title,
        description=description,
        source_tags=source_tags,
        source_categories=source_categories,
    )

    if enriched_category != discovery_category:
        logger.info(
            "[%s] category_reassigned  '%s' → '%s'  title='%.60s'",
            _NAME,
            discovery_category,
            enriched_category,
            title_raw,
        )
        data["category_slug"] = enriched_category

    # ── 2. Attribute / Facet Enrichment ──────────────────────────────────
    facets: dict = dict(data.get("facets") or {})
    facets = _enrich_facets(
        facets=facets,
        title=title,
        description=description,
        enriched_category=enriched_category,
    )
    data["facets"] = facets

    logger.debug(
        "[%s] done  category=%s  attributes=%d",
        _NAME,
        data["category_slug"],
        len(data["facets"].get("attributes", [])),
    )

    return EnrichedItemDTO(**data)


# ---------------------------------------------------------------------------
# Category re-assignment
# ---------------------------------------------------------------------------


def _enrich_category(
    discovery_category: str,
    title: str,
    description: str,
    source_tags: list[str],
    source_categories: list[str],
) -> str:
    """
    Score all known leaf categories against the content signals.
    If a candidate scores strictly higher than the discovery-assigned
    category by at least CATEGORY_CONFIDENCE_THRESHOLD points, return
    the candidate slug.  Otherwise return *discovery_category* unchanged.
    """
    if not discovery_category:
        return discovery_category

    all_slugs = list(_CATEGORY_KEYWORD_POOL.keys())

    # Score the discovery-assigned category as the baseline.
    baseline_score = _score_category_against_signals(
        discovery_category, title, description, source_tags, source_categories
    )

    best_slug = discovery_category
    best_score = baseline_score

    for slug in all_slugs:
        if slug == discovery_category:
            continue
        score = _score_category_against_signals(
            slug, title, description, source_tags, source_categories
        )
        if score > best_score:
            best_score = score
            best_slug = slug

    # Only override if the margin is significant enough.
    if best_slug != discovery_category:
        margin = best_score - baseline_score
        if margin < CATEGORY_CONFIDENCE_THRESHOLD:
            logger.debug(
                "[%s] category_hold  candidate=%s  margin=%d  threshold=%d",
                _NAME,
                best_slug,
                margin,
                CATEGORY_CONFIDENCE_THRESHOLD,
            )
            return discovery_category

    return best_slug


# ---------------------------------------------------------------------------
# Facet / attribute enrichment
# ---------------------------------------------------------------------------


def _enrich_facets(
    facets: dict,
    title: str,
    description: str,
    enriched_category: str,
) -> dict:
    """
    Extend facets with:
    * Additional attribute matches scoped to the enriched category.
    * Re-derived intent when the facets dict has no intent yet.
    * Re-derived gender when relevant to the enriched category.

    The existing values set by the classification step are preserved;
    this function only *adds* or *corrects* when missing/empty.
    """
    facets = dict(facets)  # shallow copy — do not mutate caller's dict
    text = f"{title} {description}"

    # ── Attributes ────────────────────────────────────────────────────────
    existing_attrs: set[str] = set(
        (a or "").lower() for a in facets.get("attributes", [])
    )
    new_attrs: list[str] = list(facets.get("attributes", []))

    for attr_slug, keywords in ATTRIBUTE_KEYWORD_MAP.items():
        if attr_slug in existing_attrs:
            continue
        score = _keyword_score(text, keywords)
        if score >= ATTRIBUTE_MIN_SCORE:
            new_attrs.append(attr_slug)
            existing_attrs.add(attr_slug)
            logger.debug(
                "[%s] attribute_added  slug=%s  score=%d  category=%s",
                _NAME,
                attr_slug,
                score,
                enriched_category,
            )

    facets["attributes"] = new_attrs

    # ── Intent (only fill when not already set) ───────────────────────────
    if not facets.get("intent"):
        for intent_slug, patterns in INTENT_PATTERN_MAP.items():
            if any(p in text for p in patterns):
                facets["intent"] = intent_slug
                logger.debug(
                    "[%s] intent_detected  slug=%s", _NAME, intent_slug
                )
                break

    # ── Gender (only for relevant categories, only when not already set) ──
    if not facets.get("gender") and enriched_category in GENDER_RELEVANT_ENRICHED_CATEGORIES:
        gender_keywords = {
            "men": ["for men", "men's", "mens", "male", "for him", "masculine"],
            "women": ["for women", "women's", "womens", "female", "for her", "feminine"],
        }
        for gender, patterns in gender_keywords.items():
            # Title is stronger signal
            if any(p in title for p in patterns):
                facets["gender"] = gender
                break
            if any(p in description for p in patterns):
                facets["gender"] = gender
                break

        # Default unisex when category is known-gender-relevant but signal is neutral
        if not facets.get("gender"):
            facets["gender"] = "unisex"

    return facets
