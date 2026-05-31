from app.infrastructure import cache
from app.core.extensions import db
from flask_login import current_user

@cache.memoize(timeout=60)
def get_user_context(user_id=None):
    from app.domains.user.models import User
    user = db.session.get(User, user_id) if user_id else current_user
    
    is_authenticated = user.is_authenticated
    is_admin = bool(getattr(user, "is_admin", False))
    user_email = None
    is_subscribed = False

    if is_authenticated:
        user_email = user.email

        sub = getattr(user, "newsletter_subscription", None)
        if sub and sub.is_active:
            is_subscribed = True

    return {
        "is_authenticated": is_authenticated,
        "is_admin": is_admin,
        "user_email": user_email,
        "is_subscribed": is_subscribed,
    }
