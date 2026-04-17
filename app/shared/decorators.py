# app/utils/decorators.py
from functools import wraps
from flask import abort
from flask_login import current_user


def admin_required(f):
    """
    Decorator that ensures the current user is authenticated AND is an admin.
    Apply AFTER @login_required so you never get an AnonymousUser here.

    Usage:
        @bp.route("/admin/")
        @login_required
        @admin_required
        def dashboard():
            ...

    To make yourself admin (run once in Flask shell):
        from app.core.extensions import db
        from app.domains.user.models import User
        u = User.query.filter_by(email="your@email.com").first()
        u.is_admin = True
        db.session.commit()
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated
