from app.infrastructure import cache
from app.domains.taxonomy.service import (
    get_popular_general_topics,
    get_popular_brands,
    get_active_sections,
)
from config import SOCIAL_LINKS


@cache.cached(timeout=3600, key_prefix="layout_context")
def get_layout_context():
    """
    Header + footer + shared UI data
    """

    return {
        "main_sections": get_active_sections(),
        "column_reviews": {
            "brands": get_popular_brands(),
        },
        # "popular_interests": popular_interests,
        "footer_topics": get_popular_general_topics(),
        "footer_pages": [
            {"slug": "about", "name": "About Us"},
            {"slug": "contact", "name": "Contact"},
            {"slug": "privacy", "name": "Privacy Policy"},
            {"slug": "terms", "name": "Terms"},
            {"slug": "affiliate", "name": "Affiliate Disclosure"},
        ],
        "social_links": SOCIAL_LINKS,
    }
