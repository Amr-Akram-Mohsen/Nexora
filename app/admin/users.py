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
from flask import Blueprint, jsonify, request, render_template, make_response
from app.domains.user.models import User
from app.domains.user.service import deactivate_user as deactivate_user_service, activate_user as activate_user_service
from app.core.decorators import admin_required
from app.core.extensions import db
from app.admin.helpers import parse_pagination_params
from sqlalchemy import select, or_, func

bp = Blueprint("api_user", __name__, url_prefix="/admin/users")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all user management endpoints require admin privilege."""
    pass


@bp.route("/", methods=["GET"])
def list_users():
    """Paginated user listing with optional search and role filter."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    role   = request.args.get("role", "").strip()

    stmt = select(User).order_by(User.id.desc())

    if search:
        stmt = stmt.where(
            or_(User.name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
        )
    if role:
        if role.lower() == "admin":
            stmt = stmt.where(User.is_admin == True)
        elif role.lower() == "user":
            stmt = stmt.where(User.is_admin == False)

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    serialized = [
        {
            "id":         u.id,
            "name":       u.name,
            "email":      u.email,
            "is_admin":   u.is_admin,
            "is_active":  u.is_active,
            "created_at": str(u.created_at),
        }
        for u in pagination.items
    ]

    return jsonify({
        "items":    serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/<int:id>", methods=["DELETE"])
def delete_user(id):
    success = deactivate_user_service(id)
    if not success:
        return jsonify({"error": "User not found"}), 404
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/<int:id>/activate", methods=["POST"])
def activate_user(id):
    success = activate_user_service(id)
    if not success:
        return jsonify({"error": "User not found"}), 404
    db.session.commit()
    return jsonify({"success": True})


def _build_user_query(search, role):
    """Shared query builder for users listing and rows endpoint."""
    stmt = select(User).order_by(User.id.desc())
    if search:
        stmt = stmt.where(
            or_(User.name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
        )
    if role:
        if role.lower() == "admin":
            stmt = stmt.where(User.is_admin == True)
        elif role.lower() == "user":
            stmt = stmt.where(User.is_admin == False)
    return stmt


@bp.route("/rows", methods=["GET"])
def users_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    role   = request.args.get("role", "").strip()

    stmt = _build_user_query(search, role)
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    html = render_template(
        "admin/control_panel/users/_rows.html",
        items=pagination.items,
    )
    resp = make_response(html)
    resp.headers["X-Total"] = pagination.total
    resp.headers["X-Pages"] = pagination.pages
    resp.headers["X-Page"]  = pagination.page
    return resp


@bp.route("/<int:id>/inspect", methods=["GET"])
def inspect_user(id):
    """Return server-rendered HTML for the user inspect modal body."""
    user = db.session.get(User, id)
    if not user:
        return "<p class='text-muted'>User not found.</p>", 404
    return render_template("admin/control_panel/users/_inspect.html", user=user)


@bp.route("/<int:id>/toggle-admin", methods=["POST"])
def toggle_admin(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.is_admin = not user.is_admin
    db.session.commit()
    return jsonify({"success": True, "is_admin": user.is_admin})
