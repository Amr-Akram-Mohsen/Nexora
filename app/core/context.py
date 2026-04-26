from flask_login import current_user
from flask import request, url_for
from app.domains.system.service import (
    get_popular_general_topics,
    get_popular_brands,
    get_active_sections,
)
from .extensions import cache
from config import SOCIAL_LINKS

@cache.memoize(timeout=60)
def get_user_context(user_id=None):
    from app.domains.user.models import User
    from app.core.extensions import db
    user = db.session.get(User, user_id) if user_id else current_user
    
    is_authenticated = user.is_authenticated
    user_email = None
    is_subscribed = False

    if is_authenticated:
        user_email = user.email

        sub = getattr(user, "newsletter_subscription", None)
        if sub and not sub.unsubscribed_at:
            is_subscribed = True

    return {
        "is_authenticated": is_authenticated,
        "user_email": user_email,
        "is_subscribed": is_subscribed,
    }


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


def get_global_context():
    """
    Single entry point for ALL shared template context
    """
    
    def get_filter_url(name, value, multi=True):
        args = request.args.to_dict(flat=False)
        if multi:
            current_vals = args.get(name, [])
            if value in current_vals:
                current_vals.remove(value)
                if not current_vals:
                    args.pop(name, None)
                else:
                    args[name] = current_vals
            else:
                args[name] = current_vals + [value]
        else:
            if request.args.get(name) == value:
                args.pop(name, None)
            else:
                args[name] = [value]
                
        # ensure page resets to 1 on filter change
        args.pop('page', None) 
        
        # Merge view args (e.g. section_slug)
        if request.view_args:
            for k, v in request.view_args.items():
                args[k] = v
        return url_for(request.endpoint, **args)

    def get_sort_url(sort_val):
        args = request.args.to_dict(flat=False)
        args['sort'] = [sort_val]
        if request.view_args:
            for k, v in request.view_args.items():
                args[k] = v
        return url_for(request.endpoint, **args)

    def get_page_url(page_num):
        args = request.args.to_dict(flat=False)
        args['page'] = [str(page_num)]
        if request.view_args:
            for k, v in request.view_args.items():
                args[k] = v
        return url_for(request.endpoint, **args)

    return {
        **get_user_context(current_user.id if current_user.is_authenticated else None),
        **get_layout_context(),
        "get_filter_url": get_filter_url,
        "get_sort_url": get_sort_url,
        "get_page_url": get_page_url,
        "selected_country": request.cookies.get("country", ""),
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

