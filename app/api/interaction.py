from flask import Blueprint, jsonify
from app.domains.interaction.service.query import get_comments

bp = Blueprint("api_interaction", __name__, url_prefix="/api/interactions")


@bp.route("/", methods=["GET"])
def list_comments():
    comments = get_comments()

    return jsonify([
        {
            "id": c.id,
            "content": c.content[:100],
            "user_id": c.user_id,
            "created_at": str(c.created_at)
        }
        for c in comments
    ])


@bp.route("/<int:id>", methods=["DELETE"])
# TODO: Add authentication/authorization decorator (e.g., @admin_required)
def delete_comment(id):
    from app.core.extensions import db
    from app.domains.interaction.models import Comment

    comment = db.session.get(Comment, id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    db.session.delete(comment)
    db.session.commit()

    return jsonify({"success": True})
