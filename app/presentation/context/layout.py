from app.infrastructure import cache
from app.domains.system.service import (
    get_popular_general_topics,
    get_popular_brands,
    get_active_sections,
)
from config import SOCIAL_LINKS

@cache.cached(timeout=3600, key_prefix='layout_context')
def get_layout_context():
    """
    Header + footer + shared UI data
    """
    popular_interests = get_popular_general_topics()
    popular_brands = get_popular_brands()

    return {
        "main_sections": get_active_sections(),

        "column_reviews": {
            "brands": popular_brands,
        },

        "popular_interests": popular_interests,
        "footer_topics": popular_interests,
        "footer_pages": [
            ('about', 'About Us'),
            ('contact', 'Contact'),
            ('privacy', 'Privacy Policy'),
            ('terms', 'Terms'),
            ('affiliate', 'Affiliate Disclosure'),
        ],

        "social_links": SOCIAL_LINKS,
    }
