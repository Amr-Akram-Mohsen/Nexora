GENDER_RELEVANT_CATEGORIES = {
    "perfumes",
    "watches",
    "bags",
    "sunglasses",
    "jewelry",
}

import re

GENDER_KEYWORDS = {
    "men": ["for men", "men's", "mens", "male", "for him"],
    "women": ["for women", "women's", "womens", "female", "for her", "ladies"],
}

def detect_facets(title: str, description: str, category_slug: str | None = None) -> dict:
    text = f"{title}. {description}"

    facets = {
        "intent": None,
        "price_tier": None,
        "gender": None,
        "attributes": []
    }

    # INTENT
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
    if "noise cancelling" in text:
        facets["attributes"].append("noise cancelling")
    if "waterproof" in text:
        facets["attributes"].append("waterproof")
    if "lightweight" in text:
        facets["attributes"].append("lightweight")
    if "battery life" in text:
        facets["attributes"].append("battery life")
    if "fast charging" in text:
        facets["attributes"].append("fast charging")
    if "wireless" in text:
        facets["attributes"].append("wireless")


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
