from datetime import datetime

# ==========================================================
# RECENCY
# ==========================================================

CURRENT_YEAR = datetime.utcnow().year

RECENCY_TERMS = [
    str(CURRENT_YEAR),
    f"{CURRENT_YEAR} release",
    f"{CURRENT_YEAR} trends",
    "new",
    "latest",
    "upcoming",
]


# ==========================================================
# CATEGORY -> TOPIC RELATIONSHIPS
# ==========================================================

CATEGORY_TOPIC_MAP = {
    "smartphones": ["travel-gear", "productivity", "gaming"],
    "laptops": ["home-office", "remote-work", "productivity"],
    "tablets": ["home-office", "students"],
    "smartwatches": ["fitness", "health"],
    "earbuds": ["fitness", "commuting"],
    "headphones": ["home-office", "gaming"],
    "cameras": ["photography", "travel"],
    "niche-artisanal": ["luxury"],
    "oud-oriental": ["luxury", "middle-eastern"],
    "watches": ["fashion", "fitness"],
    "bags": ["travel-gear", "everyday-carry"],
    "sunglasses": ["fashion", "summer"],
    "jewelry": ["luxury", "fashion"],
}


# ==========================================================
# DEFAULT SOURCE ALIGNMENT
# ==========================================================

DEFAULT_SOURCE_ALIGNMENT = {
    "news": ["gnews", "newsapi"],
    "reviews": ["youtube", "rss", "reddit"],
    "tutorials": ["youtube", "rss"],
    "trends": ["newsapi", "reddit"],
    "community": ["reddit"],
}


# ==========================================================
# CATEGORY SOURCE OVERRIDES
# ==========================================================

CATEGORY_SOURCE_OVERRIDES = {
    "electronics": {
        "news": ["gnews", "newsapi", "rss"],
        "trends": ["newsapi", "reddit", "rss"],
    },
    "perfumes": {
        "news": ["youtube", "reddit", "gnews"],
        "reviews": ["youtube", "reddit"],
        "tutorials": ["youtube"],
        "trends": ["reddit", "youtube"],
    },
    "accessories": {
        "news": ["rss", "newsapi", "gnews"],
        "reviews": ["youtube", "reddit", "rss"],
        "community": ["reddit"],
    },
}


# ==========================================================
# INTENT KEYWORDS (Non-Section Specific)
# ==========================================================
INTENT_KEYWORDS = {
    "Buying Guide": ["best", "buying guide"],
    "Gift Ideas": ["gift ideas", "best gifts"],
    "Comparison": ["vs", "comparison"],
    "Unboxing": ["unboxing"],
    "First Impressions": ["hands on", "first look"],
    "Value Check": ["worth it", "deal"],
    "Long-term Use": ["long term review"],
    "Technical": ["specs", "benchmarks"],
    "Lifestyle": ["aesthetic", "daily carry"],
    "News": [""],
}

# Sources that support (OR / AND / Parentheses)
BOOLEAN_SUPPORTED_SOURCES = ["newsapi", "gnews", "reddit"]

# ==========================================================
# SECTION DEFAULT INTENTS
# ==========================================================

SECTION_DEFAULT_INTENTS = {
    "news": ["News"],
    "reviews": ["Review", "First Impressions"],
    "tutorials": ["Tutorial"],
    "trends": ["Top List", "Buying Guide"],
    "community": ["Comparison", "Review"],
}


# ==========================================================
# ADVANCED QUERY TEMPLATES
# ==========================================================

QUERY_TEMPLATES = {
    "news": [
        "{category} (news OR launch OR release)",
        "{brand} (launch OR announced OR news)",
    ],
    "reviews": [
        "{category} (review OR hands-on OR {problem})",
        "best {category} {year}",
        "{brand} (review OR vs OR {problem})",
    ],
    "tutorials": [
        "{category} (setup OR guide OR tips OR {problem})",
    ],
    "trends": [
        "{category} ({feature} OR trends OR anticipated) {year}",
        "{category} buying guide {year}",
    ],
    "community": [
        "{category} (discussion OR issues OR {problem})",
        "is {category} worth it",
    ],
}


# ==========================================================
# CATEGORY -> BRAND MAP
# ==========================================================

# Expanded in app/shared/constants/query_intelligence.py
CATEGORY_BRAND_MAP = {
    "smartphones": [
        "Apple",
        "Samsung",
        "Google",
        "Xiaomi",
        "Nothing",
        "OnePlus",
        "Sony",
        "Motorola",
    ],
    "laptops": [
        "Apple",
        "Dell",
        "HP",
        "Lenovo",
        "Asus",
        "Microsoft",
        "Razer",
        "MSI",
        "Acer",
    ],
    "earbuds": ["Apple", "Sony", "Bose", "Sennheiser", "Jabra", "Beats", "Soundcore"],
    "cameras": ["Sony", "Canon", "Nikon", "Fujifilm", "Lumix", "Leica", "GoPro"],
    "perfumes": ["Dior", "Chanel", "Creed", "Tom Ford", "Armani", "Versace", "Prada"],
    "watches": [
        "Rolex",
        "Omega",
        "Seiko",
        "Tissot",
        "Casio",
        "Hamilton",
        "Tudor",
        "Cartier",
    ],
    "bags": ["Peak Design", "Bellroy", "Aer", "Nomad", "Timbuk2", "Nike", "Adidas"],
    "jewelry": ["Tiffany", "Cartier", "Pandora", "Bulgari", "Swarovski"],
}


# ==========================================================
# PROBLEM / PAIN POINT DISCOVERY
# ==========================================================

CATEGORY_PROBLEM_MAP = {
    "smartphones": [
        "battery life",
        "overheating",
        "camera quality",
        "gaming performance",
        "charging speed",
    ],
    "laptops": [
        "fan noise",
        "thermal throttling",
        "battery drain",
        "portable workstation",
    ],
    "earbuds": [
        "noise cancellation",
        "mic quality",
        "connectivity issues",
        "comfort",
    ],
    "perfumes": [
        "longevity",
        "projection",
        "summer fragrances",
        "compliment factor",
    ],
    "watches": [
        "accuracy",
        "daily wear",
        "water resistance",
    ],
}


# ==========================================================
# FEATURE / ATTRIBUTE DISCOVERY
# ==========================================================

FEATURE_MAP = {
    "bags": [
        "waterproof",
        "leather",
        "minimalist",
        "carry on",
    ],
    "watches": [
        "automatic",
        "solar",
        "field watch",
        "diver",
    ],
    "headphones": [
        "wireless",
        "ANC",
        "open back",
    ],
    "smartphones": [
        "foldable",
        "AI camera",
        "gaming",
        "budget flagship",
    ],
}


# ==========================================================
# AUDIENCE SEGMENTS
# ==========================================================

AUDIENCE_SEGMENTS = {
    "smartphones": [
        "students",
        "travelers",
        "gamers",
        "creators",
    ],
    "laptops": [
        "developers",
        "students",
        "remote work",
    ],
    "perfumes": [
        "men",
        "women",
        "office wear",
        "date night",
    ],
    "bags": [
        "travel",
        "minimalist",
        "everyday carry",
    ],
}


# ==========================================================
# SEASONAL / EVENT DISCOVERY
# ==========================================================

# Suffixes are now handled via templates or source-specific logic


# ==========================================================
# COMPARISON PATTERNS
# ==========================================================

COMPARISON_PATTERNS = [
    "{brand1} vs {brand2}",
    "{product1} vs {product2}",
    "best alternative to {brand}",
]


# ==========================================================
# RANDOMIZATION
# ==========================================================

RANDOM_QUALIFIERS = [
    "Top 5",
    "Top 10",
    "Best of",
    "New",
    "Must-have",
]


# ==========================================================
# FACET TEMPLATES
# ==========================================================

FACET_QUERY_TEMPLATES = {
    "gender": [
        "best {category} for {facet_value}",
        "{category} for {facet_value} review",
    ],
    "price_tier": [
        "best {facet_value} {category}",
        "top {facet_value} {category} {year}",
    ],
    "attributes": [
        "{category} with {facet_value}",
        "best {facet_value} {category}",
    ],
}


SOURCE_DIALECTS = {
    "youtube": {
        "news": [
            "hands on",
            "first look",
            "review",
            "vs",
        ],
        "reviews": [
            "review",
            "real world test",
            "camera test",
            "battery test",
        ],
    },
    "reddit": {
        "community": [
            "reddit",
            "worth it",
            "thoughts",
            "experience",
            "issues",
        ],
        "reviews": [
            "reddit review",
            "owner review",
            "long term review",
        ],
    },
    "newsapi": {
        "news": [
            "launch",
            "announced",
            "release",
            "unveiled",
        ]
    },
}

TEMPORAL_MODIFIERS = [
    "2026",
    "this month",
    "this week",
    "Q2 2026",
    "new",
    "latest",
]

EXPLORATION_MODIFIERS = [
    "best",
    "underrated",
    "hidden gems",
    "must buy",
    "top rated",
    "budget",
    "premium",
]

SEARCH_KEYWORD_EXPANSIONS = {
    "smartphones": "(android phone OR flagship phone OR camera phone)",
    "laptops": "(ultrabook OR gaming laptop OR creator laptop)",
    "watches": "(automatic watch OR chronograph OR dive watch)",
}


QUERY_SUFFIX_ROTATIONS = [
    "",
    "under $500",
    "for beginners",
    "for travel",
    "for gaming",
    "for productivity",
]
