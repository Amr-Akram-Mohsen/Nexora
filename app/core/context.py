from flask_login import current_user
from flask import request
from app.presentation.context.user import get_user_context
from app.presentation.context.layout import get_layout_context
from app.presentation.context.newsletter import get_newsletter_context
from app.presentation.context.filters import get_filter_url, get_sort_url, get_page_url


def get_global_context():
    """
    Single entry point for ALL shared template context
    """
    return {
        **get_user_context(current_user.id if current_user.is_authenticated else None),
        **get_layout_context(),
        "get_filter_url": get_filter_url,
        "get_sort_url": get_sort_url,
        "get_page_url": get_page_url,
        "selected_country": request.cookies.get("country", ""),
    }
