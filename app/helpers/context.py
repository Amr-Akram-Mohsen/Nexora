from flask_login import current_user
from app.services.article_service import (
    get_popular_general_topics,
    get_popular_brands,
    get_active_sections,
)
from config import SOCIAL_LINKS

def get_user_context():
    is_authenticated = current_user.is_authenticated
    user_email = None
    is_subscribed = False

    if is_authenticated:
        user_email = current_user.email

        sub = getattr(current_user, "newsletter_subscription", None)
        if sub and not sub.unsubscribed_at:
            is_subscribed = True

    return {
        "is_authenticated": is_authenticated,
        "user_email": user_email,
        "is_subscribed": is_subscribed,
    }


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

        "popular_interests": popular_interests[:5],
        "footer_topics": popular_interests[5:],
        "footer_pages": [
            ('about', 'About Us'),
            ('contact', 'Contact'),
            ('privacy', 'Privacy Policy'),
            ('terms', 'Terms'),
            ('affiliate', 'Affiliate Disclosure'),
        ],

        "social_links": SOCIAL_LINKS,
    }


def get_global_context():
    """
    Single entry point for ALL shared template context
    """
    return {
        **get_user_context(),
        **get_layout_context(),
    }

def get_newsletter_context():
    is_authenticated = current_user.is_authenticated

    subscriber = (
        current_user.newsletter_subscription
        if is_authenticated else None
    )

    is_pending = (
        subscriber
        and not subscriber.is_confirmed
        and subscriber.unsubscribed_at is None
    )

    # is_subscribed = (
    #     subscriber
    #     and subscriber.is_confirmed
    #     and subscriber.unsubscribed_at is None
    # )

    is_subscribed = (subscriber and subscriber.is_active)

    return {
        'is_authenticated': is_authenticated,
        'is_subscribed': is_subscribed,
        'is_pending': is_pending
    }

