from __future__ import annotations

# ---------------------------------------------------------------------------
# Category sets
# ---------------------------------------------------------------------------

GENDER_RELEVANT_CATEGORIES = {
    "perfumes",
    "niche-artisanal",
    "oud-oriental",
    "watches",
    "bags",
    "sunglasses",
    "jewelry",
}

PERFUME_CATEGORIES = {
    "perfumes",
    "niche-artisanal",
    "oud-oriental",
}

ELECTRONICS_CATEGORIES = {
    "smartphones",
    "laptops",
    "tablets",
    "smartwatches",
    "earbuds",
    "headphones",
    "cameras",
}

# ---------------------------------------------------------------------------
# Keyword lists
# ---------------------------------------------------------------------------

GENDER_KEYWORDS = {
    "men": ["for men", "men's", "mens", "male", "for him", "masculine", "man"],
    "women": ["for women", "women's", "womens", "female", "for her", "ladies", "feminine"],
}

# Ordered by confidence (first match wins)
PRICE_TIER_PATTERNS: list[tuple[str, list[str]]] = [
    ("luxury",    ["luxury", "high-end", "premium brand", "investment piece", "haute"]),
    ("premium",   ["premium", "flagship", "pro model", "professional"]),
    ("mid-range", ["mid-range", "mid range", "midrange", "value pick", "best value"]),
    ("budget",    ["cheap", "budget", "affordable", "under $100", "under $200", "entry level", "entry-level"]),
]

# ---------------------------------------------------------------------------
# Detect function
# ---------------------------------------------------------------------------

def detect_facets(
    title: str,
    description: str,
    category_slug: str | None = None,
    query_intent: str | None = None,
) -> dict:
    """
    Detect facets (intent, price tier, gender, attributes) from content text.

    Args:
        title: Article/video/post title.
        description: Article/video/post description or body snippet.
        category_slug: Leaf or composite category slug.
                       Composite slugs (e.g. "perfumes:niche-artisanal") are
                       normalised to their leaf automatically.
        query_intent: Intent string provided by the query context (takes
                      priority over text-derived intent).

    Returns:
        dict with keys: intent, price_tier, gender, attributes.
    """
    # Normalise composite slug → leaf
    if category_slug and ":" in category_slug:
        category_slug = category_slug.split(":")[-1]

    title_lower = (title or "").lower()
    desc_lower = (description or "").lower()
    text = f"{title_lower}. {desc_lower}"

    facets: dict = {
        "intent": query_intent.lower() if query_intent else None,
        "price_tier": None,
        "gender": None,
        "attributes": [],
    }

    # ── INTENT (only if not already provided) ────────────────────────────
    if not facets["intent"]:
        if any(w in text for w in ("hands-on", "hands on", "first look", "first impressions")):
            facets["intent"] = "first impressions"
        elif "unboxing" in text:
            facets["intent"] = "unboxing"
        elif any(w in text for w in ("review", "real-world test", "long term")):
            facets["intent"] = "review"
        elif any(w in text for w in ("best ", "top 5", "top 10", "buying guide")):
            facets["intent"] = "top list"
        elif any(w in text for w in (" vs ", " versus ", "comparison")):
            facets["intent"] = "comparison"
        elif any(w in text for w in ("how to", "setup guide", "tutorial", "tips")):
            facets["intent"] = "tutorial"
        elif any(w in text for w in ("worth it", "should you buy", "is it good")):
            facets["intent"] = "value check"

    # ── PRICE TIER ────────────────────────────────────────────────────────
    for tier, patterns in PRICE_TIER_PATTERNS:
        if any(p in text for p in patterns):
            facets["price_tier"] = tier
            break  # First match wins (ordered high→low)

    # ── ATTRIBUTES ───────────────────────────────────────────────────────

    # Universal attributes (any category)
    _add_if("noise cancelling",  ["noise cancelling", "noise canceling", "anc"], text, facets)
    _add_if("waterproof",        ["waterproof", "water resistant", "ipx", "ip68", "ip67"], text, facets)
    _add_if("battery life",      ["battery life", "long battery", "all day battery"], text, facets)
    _add_if("wireless",          ["wireless", "bluetooth"], text, facets)
    _add_if("fast charging",     ["fast charging", "quick charge", "rapid charge", "65w", "120w"], text, facets)

    # Electronics-specific
    if category_slug in ELECTRONICS_CATEGORIES:
        _add_if("foldable",          ["foldable", "flip phone", "fold"], text, facets)
        _add_if("gaming",            ["gaming", "game mode", "refresh rate 120", "144hz"], text, facets)
        _add_if("AI features",       ["ai camera", "ai feature", "on-device ai", "generative ai"], text, facets)
        _add_if("OLED display",      ["oled", "super amoled", "pro motion"], text, facets)
        _add_if("4K video",          ["4k video", "8k video", "4k recording"], text, facets)

    # Perfume-specific
    if category_slug in PERFUME_CATEGORIES:
        # Scent families
        _add_if("woody",     ["woody", "wood", "sandalwood", "cedar", "vetiver"], text, facets)
        _add_if("floral",    ["floral", "rose", "jasmine", "flower", "peony", "iris"], text, facets)
        _add_if("citrus",    ["citrus", "lemon", "orange", "bergamot", "lime", "grapefruit"], text, facets)
        _add_if("spicy",     ["spicy", "pepper", "cinnamon", "cardamom", "clove"], text, facets)
        _add_if("musky",     ["musk", "musky", "musky"], text, facets)
        _add_if("gourmand",  ["vanilla", "caramel", "chocolate", "gourmand"], text, facets)
        _add_if("oud",       ["oud", "agarwood", "oud oil"], text, facets)
        # Performance
        _add_if("long-lasting",   ["long lasting", "longevity", "beast mode", "all day", "long-lasting"], text, facets)
        _add_if("high projection", ["strong projection", "beast", "sillage"], text, facets)
        _add_if("winter-wear",     ["winter", "cold weather", "autumn", "fall"], text, facets)
        _add_if("summer-wear",     ["summer", "hot weather", "fresh", "heat"], text, facets)

    # Watch-specific
    if category_slug == "watches":
        _add_if("automatic",   ["automatic", "self-winding", "mechanical"], text, facets)
        _add_if("solar",       ["solar", "solar powered", "eco drive"], text, facets)
        _add_if("diver",       ["diver", "dive watch", "200m", "300m"], text, facets)
        _add_if("chronograph", ["chronograph", "chrono", "stopwatch"], text, facets)

    # Bag-specific
    if category_slug == "bags":
        _add_if("leather",     ["genuine leather", "full grain leather", "leather bag"], text, facets)
        _add_if("minimalist",  ["minimalist", "slim profile", "clean design"], text, facets)

    # ── GENDER (strict, category-gated) ──────────────────────────────────
    if category_slug in GENDER_RELEVANT_CATEGORIES:
        for gender, patterns in GENDER_KEYWORDS.items():
            # 1. Title (high confidence)
            if any(p in title_lower for p in patterns):
                facets["gender"] = gender
                break
            # 2. Description (lower confidence)
            if any(p in desc_lower for p in patterns):
                facets["gender"] = gender
                break

    return facets


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _add_if(attribute: str, keywords: list[str], text: str, facets: dict) -> None:
    """Add *attribute* to facets["attributes"] if any keyword matches."""
    if attribute not in facets["attributes"] and any(kw in text for kw in keywords):
        facets["attributes"].append(attribute)
