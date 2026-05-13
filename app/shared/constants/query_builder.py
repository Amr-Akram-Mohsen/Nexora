
CATEGORY_TOPIC_MAP = {
    # Electronics
    "smartphones": ["travel-gear"],   # used on the go
    "laptops": ["home-office"],
    "tablets": ["home-office"],
    "smartwatches": ["fitness"],
    "earbuds": ["fitness"],
    "headphones": ["home-office"],
    "cameras": ["photography"],

    # Perfumes
    "niche-artisanal": [],
    "oud-oriental": [],

    # Accessories
    "watches": ["fitness"],            # smart watches overlap
    "bags": ["travel-gear"],
    "sunglasses": ["travel-gear"],
    "jewelry": [],
}


# Default source alignment by section slug.
DEFAULT_SOURCE_ALIGNMENT = {
    "news":       ["gnews", "newsapi"],
    "reviews":    ["youtube", "rss", "reddit"], # Added Reddit for 'real' opinions
    "tutorials":  ["youtube", "rss"],
    "trends":     ["newsapi", "reddit"],
    "community":  ["reddit"],
}

# Category-specific overrides based on source bias (e.g. Perfumes = Community/Influencer driven).
CATEGORY_SOURCE_OVERRIDES = {
    "electronics": {
        "news":   ["gnews", "newsapi", "rss"],
        "trends": ["newsapi", "reddit", "rss"],
    },
    "perfumes": {
        "news":      ["youtube", "reddit", "gnews"],  # gnews added — covers fragrance news
        "reviews":   ["youtube", "reddit"],
        "tutorials": ["youtube"],
        "trends":    ["reddit", "youtube"],
    },
    "accessories": {
        "news":      ["rss", "newsapi", "gnews"],      # gnews added — covers fashion/watch news
        "reviews":   ["youtube", "reddit", "rss"],
        "community": ["reddit"],
    }
}

# Intent-based keyword map to refine search phrases.
INTENT_KEYWORDS = {
    "Buying Guide":      ["buying guide", "best", "what to buy"],
    "Gift Ideas":        ["gift ideas", "best gifts"],
    "Comparison":        ["vs", "comparison", "or"],
    "Top List":          ["top", "best", "ranked"],
    "Unboxing":          ["unboxing"],
    "First Impressions": ["first impressions", "hands on"],
    "Review":            ["review", "worth it"],
    "News":              ["launch", "release", "announced"],
    "Tutorial":          ["how to", "guide", "tips"]
}

# Maps sections to their natural "Intents".
SECTION_DEFAULT_INTENTS = {
    "news":       ["News"],
    "reviews":    ["Review", "First Impressions"],
    "tutorials":  ["Tutorial"],
    "trends":     ["Top List", "Buying Guide"],
    "community":  ["Comparison", "Review"]
}

# Advanced templates for more natural and focused search results.
QUERY_TEMPLATES = {
    "news": [
        "{category} news",
        "{category} launch OR announcement",
        "new {category} releases",
    ],
    "reviews": [
        "{category} review",
        "best {category} {year}",
        "{category} hands-on impressions",
        "{category} comparison vs",
    ],
    "tutorials": [
        "how to use {category}",
        "{category} setup guide",
        "{category} tips and tricks",
        "{category} maintenance and care",
    ],
    "trends": [
        "{category} market trends {year}",
        "future of {category}",
        "most anticipated {category}",
    ],
    "community": [
        "{category} discussion",
        "{category} user feedback",
        "{category} problems OR issues",
        "is {category} worth it",
    ],
}

# Maps categories to their power-house brands for targeted news/review discovery.
CATEGORY_BRAND_MAP = {
    "smartphones":  ["Apple", "Samsung", "Google", "Xiaomi"],
    "laptops":      ["Apple", "Dell", "HP", "Lenovo", "Asus"],
    "smartwatches": ["Apple", "Samsung", "Garmin"],
    "cameras":      ["Sony", "Canon", "Nikon", "Fujifilm"],
    "perfumes":     ["Dior", "Chanel", "Creed", "Tom Ford"],
    "watches":      ["Rolex", "Omega", "Seiko", "Tissot"],
}


# Facet-specific templates to target attributes like price, gender, or seasonal use.
FACET_QUERY_TEMPLATES = {
    "gender":      ["best {category} for {facet_value}", "{category} for {facet_value} review"],
    "price_tier":  ["best {facet_value} {category}", "top {facet_value} {category} {year}"],
    "attributes":  ["{category} with {facet_value}", "best {facet_value} {category}"],
}
