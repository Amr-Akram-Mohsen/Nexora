from flask import Blueprint, jsonify, request
from app.domains.user.service import get_users, deactivate_user as deactivate_user_service, activate_user as activate_user_service
from app.domains.user.models import User
from app.core.decorators import admin_required
from app.core.extensions import db

bp = Blueprint("api_user", __name__, url_prefix="/admin/users")


# @bp.before_request
# @admin_required
# def require_admin():
#     """Ensure all users endpoints require admin privilege."""
#     pass


@bp.route("/", methods=["GET"])
def list_users():
    search = request.args.get('search')
    role = request.args.get('role')
    users = get_users(search=search, role=role)

    return jsonify([
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "created_at": str(u.created_at)
        }
        for u in users
    ])


@bp.route("/<int:id>", methods=["DELETE"])
@admin_required
def delete_user(id):
    success = deactivate_user_service(id)

    if not success:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"success": True})


@bp.route("/<int:id>/activate", methods=["POST"])
@admin_required
def activate_user(id):
    success = activate_user_service(id)

    if not success:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"success": True})


@bp.route("/<int:id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(id):
    user = db.session.get(User, id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    user.is_admin = not user.is_admin
    db.session.commit()

    return jsonify({"success": True, "is_admin": user.is_admin})
