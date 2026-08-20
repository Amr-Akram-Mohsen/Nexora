"""
Admin user management endpoints.
"""
from flask import Blueprint, jsonify, request, render_template
from app.domains.user.service.admin.admin import get_admin_users_paginated
from app.application.user.admin import (
    deactivate_user_workflow,
    activate_user_workflow,
    toggle_admin_user_workflow,
    get_user_inspect_workflow,
)
from app.domains.user.service.admin.analytics import get_user_dashboard_stats
from app.domains.user.serializers import serialize_user_row
from app.web.routes.admin.helpers import (
    apply_admin_guard,
    parse_pagination_params,
    render_admin_rows_response,
)
from app.web.routes.admin.builders.user_builder import build_user_inspect_view_model

bp = Blueprint("api_user", __name__, url_prefix="/admin/users")
apply_admin_guard(bp)


@bp.route("/stats", methods=["GET"])
def users_stats():
    """Return JSON metrics for the users dashboard charts."""
    return jsonify(get_user_dashboard_stats())


def _paginate_manual(search, role, status, verified, subscription, provider, sort_by, sort_dir, page, per_page):
    return get_admin_users_paginated(search, role, status, verified, subscription, provider, sort_by, sort_dir, page, per_page)



@bp.route("/", methods=["GET"])
def list_users():
    """Paginated user listing with optional search and role filter."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    role = request.args.get("user_role_filter", "").strip()
    status = request.args.get("user_status_filter", "").strip()
    verified = request.args.get("user_verified_filter", "").strip()
    subscription = request.args.get("user_subscription_filter", "").strip()
    provider = request.args.get("user_provider_filter", "").strip()
    sort_by = request.args.get("sort_by", "").strip()
    sort_dir = request.args.get("sort_dir", "desc").strip()

    products, total, pages, stats = _paginate_manual(search, role, status, verified, subscription, provider, sort_by, sort_dir, page, per_page)
    serialized = [serialize_user_row(u, score) for u, score in products]

    return jsonify({
        "products": serialized,
        "page": page,
        "pages": pages,
        "total": total,
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


@bp.route("/rows", methods=["GET"])
def users_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    role = request.args.get("user_role_filter", "").strip()
    status = request.args.get("user_status_filter", "").strip()
    verified = request.args.get("user_verified_filter", "").strip()
    subscription = request.args.get("user_subscription_filter", "").strip()
    provider = request.args.get("user_provider_filter", "").strip()
    sort_by = request.args.get("sort_by", "").strip()
    sort_dir = request.args.get("sort_dir", "desc").strip()

    products, total, pages, stats = _paginate_manual(search, role, status, verified, subscription, provider, sort_by, sort_dir, page, per_page)
    users = [serialize_user_row(u, score) for u, score in products]

    resp = render_admin_rows_response(
        users,
        "user",
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
