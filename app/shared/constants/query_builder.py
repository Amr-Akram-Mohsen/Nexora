
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


QUERY_TEMPLATES = {
    "news": [
        "{category} news",
        "{category} launch",
        "{category} announcement",
        "new {category} release",
    ],
    "reviews": [
        "{category} review OR hands-on",
        "best {category} {year}",
        "{category} test OR impressions",
        "{category} full review",
    ],
    "tutorials": [
        "how to use {category}",
        "{category} guide",
        "{category} tips and tricks",
    ],
    "trends": [
        "{category} trends {year}",
        "future of {category}",
        "{category} upcoming releases",
    ],
    "community": [
        "{category} discussion",
        "{category} user opinions",
    ],
}
