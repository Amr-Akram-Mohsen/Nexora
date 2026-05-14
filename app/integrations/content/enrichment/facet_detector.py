GENDER_RELEVANT_CATEGORIES = {
    "perfumes",
    "watches",
    "bags",
    "sunglasses",
    "jewelry",
}

GENDER_KEYWORDS = {
    "men": ["for men", "men's", "mens", "male", "for him"],
    "women": ["for women", "women's", "womens", "female", "for her", "ladies"],
}


def detect_facets(
    title: str,
    description: str,
    category_slug: str | None = None,
    query_intent: str | None = None,
) -> dict:
    text = f"{title}. {description}".lower()

    facets = {
        "intent": query_intent.lower() if query_intent else None,
        "price_tier": None,
        "gender": None,
        "attributes": [],
    }

    # INTENT (only if not already provided by query)
    if not facets["intent"]:
        if "review" in text or "hands on" in text:
            facets["intent"] = "review"
        elif "best" in text or "top" in text:
            facets["intent"] = "top list"
        elif "vs" in text or "comparison" in text:
            facets["intent"] = "comparison"
        elif "guide" in text or "how to" in text:
            facets["intent"] = "buying guide"
        elif "unboxing" in text:
            facets["intent"] = "unboxing"
        elif "first impressions" in text:
            facets["intent"] = "first impressions"

    # PRICE
    if "cheap" in text or "budget" in text:
        facets["price_tier"] = "budget"
    elif "mid-range" in text:
        facets["price_tier"] = "mid-range"
    elif "premium" in text:
        facets["price_tier"] = "premium"
    elif "luxury" in text:
        facets["price_tier"] = "luxury"

    # ATTRIBUTES
    # General
    if "noise cancelling" in text:
        facets["attributes"].append("noise cancelling")
    if "waterproof" in text:
        facets["attributes"].append("waterproof")
    if "battery life" in text:
        facets["attributes"].append("battery life")

    # Perfume Specific
    if category_slug in ["perfumes", "niche-artisanal", "oud-oriental"]:
        # Scent Profiles
        if any(w in text for w in ["woody", "wood", "sandalwood", "cedar"]):
            facets["attributes"].append("woody")
        if any(w in text for w in ["floral", "rose", "jasmine", "flower"]):
            facets["attributes"].append("floral")
        if any(w in text for w in ["citrus", "lemon", "orange", "bergamot"]):
            facets["attributes"].append("citrus")
        if any(w in text for w in ["spicy", "pepper", "cinnamon", "cardamom"]):
            facets["attributes"].append("spicy")
        if any(w in text for w in ["musk", "musky"]):
            facets["attributes"].append("musky")

        # Performance
        if any(
            w in text for w in ["long lasting", "longevity", "beast mode", "all day"]
        ):
            facets["attributes"].append("long-lasting")
        if any(w in text for w in ["winter", "cold weather"]):
            facets["attributes"].append("winter-wear")
        if any(w in text for w in ["summer", "hot weather", "fresh"]):
            facets["attributes"].append("summer-wear")

    # ── GENDER (STRICT) ────────────────────────
    if category_slug in GENDER_RELEVANT_CATEGORIES:
        for gender, patterns in GENDER_KEYWORDS.items():
            # 1. Prefer title (high confidence)
            if any(pattern in title for pattern in patterns):
                facets["gender"] = gender
                break

            # 2. Fallback to description (lower confidence)
            if any(pattern in description for pattern in patterns):
                facets["gender"] = gender
                break

    return facets
