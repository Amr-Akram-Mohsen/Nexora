from flask import Blueprint, jsonify, request
from app.domains.user.service import get_users, deactivate_user
from app.core.decorators import admin_required

bp = Blueprint("api_user", __name__, url_prefix="/api/users")


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
            "created_at": str(u.created_at)
        }
        for u in users
    ])


@bp.route("/<int:id>", methods=["DELETE"])
@admin_required
def delete_user(id):
    from app.core.extensions import db
    from app.domains.user.models import User

    user = db.session.get(User, id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({"success": True})
