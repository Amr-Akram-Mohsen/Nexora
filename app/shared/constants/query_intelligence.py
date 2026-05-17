from datetime import datetime

# ==========================================================
# RECENCY
# ==========================================================

_now = datetime.utcnow()
CURRENT_YEAR = _now.year
_CURRENT_QUARTER = f"Q{(_now.month - 1) // 3 + 1}"

RECENCY_TERMS = [
    str(CURRENT_YEAR),
    f"{CURRENT_YEAR} release",
    f"{CURRENT_YEAR} trends",
    "new",
    "latest",
    "upcoming",
]


# ==========================================================
# CATEGORY VELOCITY
# Used to scale cooldown duration per category.
# High-velocity: new content daily (shorter cooldown).
# Low-velocity: new content weekly or less (longer cooldown).
# ==========================================================

CATEGORY_VELOCITY: dict[str, str] = {
    # High velocity — daily news, launches, leaks
    "smartphones": "high",
    "laptops": "high",
    "tablets": "high",
    "smartwatches": "high",
    "earbuds": "medium",
    "headphones": "medium",
    "cameras": "medium",
    # Low velocity — evergreen / niche / slow-moving
    "niche-artisanal": "low",
    "oud-oriental": "low",
    "perfumes": "low",
    "watches": "low",
    "bags": "low",
    "sunglasses": "low",
    "jewelry": "low",
}

# Multipliers applied to the source profile's base cooldown_hours.
# high   → 0.25× (e.g. 24h base → 6h effective)
# medium → 0.5×  (e.g. 24h base → 12h effective)
# low    → 2.0×  (e.g. 24h base → 48h effective)
VELOCITY_COOLDOWN_MULTIPLIER: dict[str, float] = {
    "high": 0.25,
    "medium": 0.5,
    "low": 2.0,
}


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
    "Review": ["review", "hands-on", "real world test"],
    "Buying Guide": ["best", "buying guide", "worth it"],
    "Gift Ideas": ["gift ideas", "best gifts"],
    "Comparison": ["vs", "comparison", "versus"],
    "Unboxing": ["unboxing", "first look"],
    "First Impressions": ["hands on", "first impressions", "early review"],
    "Value Check": ["worth it", "budget", "best deal"],
    "Long-term Use": ["long term review", "after 6 months"],
    "Technical": ["specs", "benchmarks", "performance test"],
    "Lifestyle": ["aesthetic", "daily carry", "everyday use"],
    "Tutorial": ["how to", "setup guide", "tips and tricks"],
    "Top List": ["best", "top 5", "top 10"],
    "News": ["launch", "announced", "release", "unveiled"],
}

# Sources that support (OR / AND / Parentheses)
BOOLEAN_SUPPORTED_SOURCES = ["newsapi", "reddit"]

# ==========================================================
# SECTION DEFAULT INTENTS
# ==========================================================

SECTION_DEFAULT_INTENTS = {
    "news": ["News"],
    "reviews": ["Review"],  # "First Impressions" generates near-identical queries
    "tutorials": ["Tutorial"],
    "trends": ["Top List"],  # "Buying Guide" overlaps heavily with "Top List"
    "community": ["Comparison"],  # "Review" is already covered by the reviews section
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
        # Category-first template: broad discovery
        "{category} (review OR hands-on OR {problem})",
        # Year-anchored template: surfaces recent content
        "best {category} {year}",
        # Brand-specific template is intentionally removed: selected_brand is
        # already injected as a separate entry in expanded_terms, so
        # "{brand} review" is generated naturally via the category template.
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
        "Google Pixel",
        "Xiaomi",
        "Nothing Phone",
        "OnePlus",
        "Sony Xperia",
        "Motorola",
        "Oppo",
        "Vivo",
    ],
    "laptops": [
        "Apple MacBook",
        "Dell XPS",
        "HP Spectre",
        "Lenovo ThinkPad",
        "Asus ZenBook",
        "Microsoft Surface",
        "Razer Blade",
        "MSI",
        "Acer Swift",
        "Samsung Galaxy Book",
    ],
    "tablets": [
        "Apple iPad",
        "Samsung Galaxy Tab",
        "Microsoft Surface",
        "Lenovo Tab",
        "Xiaomi Pad",
    ],
    "smartwatches": [
        "Apple Watch",
        "Samsung Galaxy Watch",
        "Garmin",
        "Fitbit",
        "Amazfit",
        "Fossil",
        "Huawei Watch",
    ],
    "earbuds": [
        "Apple AirPods",
        "Sony WF",
        "Bose QuietComfort",
        "Samsung Galaxy Buds",
        "Jabra Elite",
        "Beats Fit",
        "Soundcore Liberty",
        "Sennheiser Momentum",
    ],
    "headphones": [
        "Sony WH",
        "Bose QuietComfort",
        "Sennheiser HD",
        "Apple AirPods Max",
        "Beyerdynamic",
        "Audio-Technica",
        "Jabra Evolve",
    ],
    "cameras": [
        "Sony Alpha",
        "Canon EOS",
        "Nikon Z",
        "Fujifilm X",
        "Lumix S",
        "Leica M",
        "GoPro Hero",
        "DJI Osmo",
    ],
    "perfumes": [
        "Dior Sauvage",
        "Chanel",
        "Creed Aventus",
        "Tom Ford",
        "Armani",
        "Versace",
        "Prada",
        "YSL",
        "Maison Margiela",
        "Acqua di Parma",
    ],
    "niche-artisanal": [
        "Byredo",
        "Le Labo",
        "Diptyque",
        "Memo Paris",
        "Xerjoff",
        "Nishane",
        "Initio",
        "Parfums de Marly",
    ],
    "oud-oriental": [
        "Swiss Arabian",
        "Al Haramain",
        "Ajmal",
        "Rasasi",
        "Lattafa",
        "Orientica",
        "Afnan",
        "Amouage",
    ],
    "watches": [
        "Rolex",
        "Omega Seamaster",
        "Seiko",
        "Tissot PRX",
        "Casio G-Shock",
        "Hamilton Khaki",
        "Tudor Black Bay",
        "Cartier",
        "Longines",
    ],
    "bags": [
        "Peak Design",
        "Bellroy",
        "Aer Pack",
        "Tumi",
        "Louis Vuitton",
        "Gucci",
        "Coach",
        "Fjallraven Kanken",
    ],
    "sunglasses": [
        "Ray-Ban",
        "Oakley",
        "Persol",
        "Maui Jim",
        "Tom Ford",
        "Warby Parker",
        "Gentle Monster",
    ],
    "jewelry": [
        "Tiffany & Co",
        "Cartier",
        "Pandora",
        "Bulgari",
        "Swarovski",
        "Van Cleef",
        "Mejuri",
    ],
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
        "fast charging",
        "drop durability",
    ],
    "laptops": [
        "fan noise",
        "thermal throttling",
        "battery drain",
        "screen quality",
        "keyboard comfort",
    ],
    "tablets": [
        "stylus support",
        "battery life",
        "multitasking",
        "screen brightness",
    ],
    "earbuds": [
        "noise cancellation",
        "mic quality",
        "call quality",
        "fit and comfort",
        "connection drops",
    ],
    "headphones": [
        "noise isolation",
        "comfort for long sessions",
        "soundstage",
        "wireless latency",
    ],
    "cameras": [
        "low light performance",
        "autofocus speed",
        "video stabilization",
        "battery life",
        "weather sealing",
    ],
    "smartwatches": [
        "battery life",
        "health tracking accuracy",
        "always on display",
        "third party apps",
    ],
    "perfumes": [
        "longevity",
        "sillage",
        "seasonal versatility",
        "office appropriate",
    ],
    "niche-artisanal": [
        "longevity",
        "uniqueness",
        "bottle design",
        "value for money",
    ],
    "oud-oriental": [
        "oud intensity",
        "longevity",
        "projection",
        "halal certification",
    ],
    "watches": [
        "accuracy",
        "daily wear durability",
        "water resistance",
        "strap comfort",
    ],
    "bags": [
        "durability",
        "airport carry-on size",
        "organization pockets",
        "waterproofing",
    ],
    "jewelry": [
        "tarnish resistance",
        "hypoallergenic",
        "gold plating durability",
    ],
}


# ==========================================================
# FEATURE / ATTRIBUTE DISCOVERY
# ==========================================================

FEATURE_MAP = {
    "smartphones": [
        "foldable display",
        "AI camera",
        "gaming mode",
        "budget flagship",
        "periscope zoom",
        "satellite connectivity",
    ],
    "laptops": [
        "OLED display",
        "thin and light",
        "gaming",
        "creator workstation",
        "long battery",
        "touchscreen",
    ],
    "tablets": [
        "OLED screen",
        "stylus support",
        "desktop mode",
        "gaming tablet",
    ],
    "earbuds": [
        "ANC",
        "transparency mode",
        "spatial audio",
        "multi-point connection",
        "waterproof",
    ],
    "headphones": [
        "wireless ANC",
        "open back",
        "planar magnetic",
        "Hi-Res audio",
    ],
    "cameras": [
        "mirrorless",
        "full frame",
        "4K video",
        "compact",
        "action cam",
    ],
    "smartwatches": [
        "ECG monitor",
        "blood oxygen",
        "GPS running",
        "rugged outdoors",
        "AMOLED display",
    ],
    "bags": [
        "waterproof",
        "leather",
        "minimalist",
        "carry-on approved",
        "laptop compartment",
    ],
    "watches": [
        "automatic movement",
        "solar powered",
        "field watch",
        "diver watch",
        "dress watch",
    ],
    "perfumes": [
        "long lasting",
        "office safe",
        "date night",
        "summer scent",
        "winter warmer",
    ],
    "niche-artisanal": [
        "artisan crafted",
        "natural ingredients",
        "limited edition",
        "avant-garde",
    ],
    "oud-oriental": [
        "pure oud",
        "rose oud",
        "amber base",
        "musk and wood",
    ],
    "jewelry": [
        "gold vermeil",
        "sterling silver",
        "diamond",
        "minimalist design",
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
    str(CURRENT_YEAR),
    "this month",
    "this week",
    f"{_CURRENT_QUARTER} {CURRENT_YEAR}",
    "new",
    "latest",
]

EXPLORATION_MODIFIERS = [
    "best",
    "underrated",
    "must buy",
    "top rated",
    "budget",
    "premium",
]

SEARCH_KEYWORD_EXPANSIONS = {
    # Electronics
    "smartphones": "(android phone OR flagship phone OR camera phone OR mobile phone)",
    "laptops": "(ultrabook OR gaming laptop OR creator laptop OR MacBook OR notebook)",
    "tablets": "(iPad OR android tablet OR drawing tablet OR e-reader)",
    "smartwatches": "(fitness tracker OR smart band OR wearable OR GPS watch)",
    "earbuds": "(wireless earbuds OR true wireless OR in-ear headphones OR AirPods)",
    "headphones": "(over-ear headphones OR noise cancelling OR wireless headset)",
    "cameras": "(mirrorless camera OR DSLR OR action camera OR compact camera)",
    # Perfumes
    "perfumes": "(fragrance OR cologne OR eau de parfum OR scent OR perfume review)",
    "niche-artisanal": "(niche fragrance OR artisan perfume OR indie scent OR niche perfume)",
    "oud-oriental": "(oud fragrance OR oriental perfume OR arabic perfume OR bakhoor)",
    # Accessories
    "watches": "(automatic watch OR chronograph OR dive watch OR luxury watch)",
    "bags": "(backpack review OR leather bag OR travel bag OR everyday carry)",
    "sunglasses": "(polarized sunglasses OR UV protection OR designer sunglasses)",
    "jewelry": "(gold jewelry OR silver jewelry OR minimalist jewelry OR fine jewelry)",
}


# Suffix rotations — added to queries on a deterministic slot cycle.
# Keep these category-neutral and realistic. Do NOT add category-specific
# terms here (those belong in FEATURE_MAP / CATEGORY_PROBLEM_MAP).
QUERY_SUFFIX_ROTATIONS = [
    "",  # No suffix (most common — keeps query clean)
    "under $500",
    "for beginners",
    "for travel",
    "worth buying",
]
