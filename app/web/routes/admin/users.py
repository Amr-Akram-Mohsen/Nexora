# app/admin/users.py
"""
Admin user management endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- Listing now returns a proper paginated envelope {items, page, pages, total, per_page}
  instead of a flat array limited to 10 results (R-09).
- Normalized to LF line endings (R-24).
- Added /rows HTML partial endpoint and /<id>/inspect HTML endpoint for Jinja AJAX architecture.
"""
from flask import Blueprint, jsonify, request, render_template
from app.domains.user.models import User
from app.domains.user.service.admin import get_admin_users_paginated
from app.application.user.admin import deactivate_user_workflow, activate_user_workflow, toggle_admin_user_workflow
from app.web.routes.admin.helpers import apply_admin_guard
from app.core.extensions import db
from app.web.routes.admin.helpers import parse_pagination_params, make_rows_response
from sqlalchemy import select, or_, and_, func
from app.domains.taxonomy.models import Category, Topic, Brand
from app.domains.interaction.models import Comment, Reaction, View, Save, Share, ItemClick, RecommendationImpression, RecommendationClick
from app.domains.recommendation.models import UserInterest, UserEntityInterest

bp = Blueprint("api_user", __name__, url_prefix="/admin/users")

@bp.route("/stats", methods=["GET"])
def users_stats():
    """Return JSON metrics for the users dashboard charts."""
    from app.domains.user.service.analytics import get_user_dashboard_stats
    return jsonify(get_user_dashboard_stats())


apply_admin_guard(bp)


def _paginate_manual(search, role, status, verified, subscription, provider, sort_by, sort_dir, page, per_page):
    return get_admin_users_paginated(search, role, status, verified, subscription, provider, sort_by, sort_dir, page, per_page)

@bp.route("/", methods=["GET"])
def list_users():
    """Paginated user listing with optional search and role filter."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    role   = request.args.get("user_role_filter", "").strip()
    status = request.args.get("user_status_filter", "").strip()
    verified = request.args.get("user_verified_filter", "").strip()
    subscription = request.args.get("user_subscription_filter", "").strip()
    provider = request.args.get("user_provider_filter", "").strip()
    sort_by = request.args.get("sort_by", "").strip()
    sort_dir = request.args.get("sort_dir", "desc").strip()

    items, total, pages, stats = _paginate_manual(search, role, status, verified, subscription, provider, sort_by, sort_dir, page, per_page)

    serialized = []
    for u, score in items:
        serialized.append({
            "id":         u.id,
            "name":       u.name,
            "email":      u.email,
            "is_admin":   u.is_admin,
            "is_active":  u.is_active,
            "created_at": str(u.created_at),
            "last_login_at": str(u.last_login_at) if u.last_login_at else None,
            "engagement_score": score or 0,
        })

    return jsonify({
        "items":    serialized,
        "page":     page,
        "pages":    pages,
        "total":    total,
        "per_page": per_page,
    })


@bp.route("/<int:id>", methods=["DELETE"])
def delete_user(id):
    success = deactivate_user_workflow(id)
    if not success:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"success": True})


@bp.route("/<int:id>/activate", methods=["POST"])
def activate_user(id):
    success = activate_user_workflow(id)
    if not success:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"success": True})


def _build_user_query(search, role, status, verified, subscription, provider, sort_by=None, sort_dir=None):
    from app.domains.user.service.analytics import build_user_query as domain_build_user_query
    return domain_build_user_query(search, role, status, verified, subscription, provider, sort_by, sort_dir)


@bp.route("/rows", methods=["GET"])
def users_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    role   = request.args.get("user_role_filter", "").strip()
    status = request.args.get("user_status_filter", "").strip()
    verified = request.args.get("user_verified_filter", "").strip()
    subscription = request.args.get("user_subscription_filter", "").strip()
    provider = request.args.get("user_provider_filter", "").strip()
    sort_by = request.args.get("sort_by", "").strip()
    sort_dir = request.args.get("sort_dir", "desc").strip()

    items, total, pages, stats = _paginate_manual(search, role, status, verified, subscription, provider, sort_by, sort_dir, page, per_page)

    users = []
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for u, score in items:
        recency_days = (now - u.last_login_at).days if u.last_login_at else None
        users.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "is_verified": u.is_verified,
            "is_admin": u.is_admin,
            "is_subscribed": bool(u.newsletter_subscription and u.newsletter_subscription.is_active),
            "is_active": u.is_active,
            "created_at": u.created_at.strftime("%Y-%m-%d") if u.created_at else None,
            "last_login_at": u.last_login_at.strftime("%Y-%m-%d %H:%M") if u.last_login_at else None,
            "recency_days": recency_days,
            "engagement_score": float(score) if score else 0.0,
        })

    html = render_template(
        "admin/components/_rows.html",
        items=users,
        domain_type="user"
    )
    resp = make_rows_response(
        html,
        total=total,
        pages=pages,
        page=page,
    )
    resp.headers["X-Active-Count"] = stats["active"]
    resp.headers["X-Admin-Count"] = stats["admins"]
    resp.headers["X-Verified-Count"] = stats["verified"]
    resp.headers["X-Subscribed-Count"] = stats["subscribed"]
    return resp


@bp.route("/<int:id>/inspect", methods=["GET"])
def inspect_user(id):
    from app.application.user.admin import get_user_inspect_workflow
    from app.web.routes.admin.builders.user_builder import build_user_inspect_view_model
    
    aggregated_data = get_user_inspect_workflow(id)
    if not aggregated_data:
        return jsonify({"error": "User not found"}), 404
        
    data = build_user_inspect_view_model(aggregated_data)
    data["domain"] = "users"
    return render_template("admin/components/_inspect.html", **data)





@bp.route("/<int:id>/toggle-admin", methods=["POST"])
def toggle_admin(id):
    user = toggle_admin_user_workflow(id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"success": True, "is_admin": user.is_admin})
