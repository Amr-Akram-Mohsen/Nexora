from app.infrastructure import cache
from app.core.extensions import db
from flask_login import current_user
from flask import session

@cache.memoize(timeout=60)
def _get_user_context_cached(user_id):
    from app.domains.user.models import User
    user = db.session.get(User, user_id) if user_id else current_user
    
    is_authenticated = user.is_authenticated
    is_admin = bool(getattr(user, "is_admin", False))
    user_email = None
    is_subscribed = False
    user_name = None

    if is_authenticated:
        user_email = user.email
        user_name = user.name

        sub = getattr(user, "newsletter_subscription", None)
        if sub and sub.is_active:
            is_subscribed = True

    return {
        "is_authenticated": is_authenticated,
        "is_admin": is_admin,
        "user_email": user_email,
        "user_name": user_name,
        "is_subscribed": is_subscribed,
    }

def get_user_context(user_id=None):
    context = _get_user_context_cached(user_id).copy()
    
    multi_accounts = []
    if context.get("is_authenticated"):
        existing_accounts = session.get("multi_accounts", [])
        from app.domains.user.models import User
        
        for aid in existing_accounts:
            u = db.session.get(User, aid)
            if u:
                multi_accounts.append({
                    "id": u.id,
                    "email": u.email,
                    "name": u.name or "Nexora Member",
                    "avatar_letter": u.email[0].upper() if u.email else "U",
                    "is_active": u.id == current_user.id
                })
        
        # Ensure current user is in the list
        if not any(a["id"] == current_user.id for a in multi_accounts):
            multi_accounts.append({
                "id": current_user.id,
                "email": current_user.email,
                "name": current_user.name or "Nexora Member",
                "avatar_letter": current_user.email[0].upper() if current_user.email else "U",
                "is_active": True
            })

    context["multi_accounts"] = multi_accounts
    return context
