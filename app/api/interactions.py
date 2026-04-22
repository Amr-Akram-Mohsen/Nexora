from flask import Blueprint, jsonify
from app.core.decorators import admin_required

from app.domains.interaction.service.query import (
    get_comments,
    get_interactions_breakdown,
    get_reaction_stats,
    get_view_stats,
    get_save_stats,
    get_click_stats,
)

from app.domains.interaction.service.command import (
    delete_comment as delete_comment_service,
)

bp = Blueprint("api_interaction", __name__, url_prefix="/api/interactions")


# ---------------------------
# COMMENTS
# ---------------------------

@bp.route("/comments", methods=["GET"])
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


@bp.route("/comments/<int:id>", methods=["DELETE"])
@admin_required
def delete_comment(id):
    success = delete_comment_service(id)

    if not success:
        return jsonify({"error": "Comment not found"}), 404

    return jsonify({"success": True})


# ---------------------------
# STATS (DASHBOARD)
# ---------------------------

@bp.route("/stats", methods=["GET"])
def interactions_stats():
    return jsonify(get_interactions_breakdown())


@bp.route("/reactions/stats", methods=["GET"])
def reactions_stats():
    return jsonify(get_reaction_stats())


@bp.route("/views/stats", methods=["GET"])
def views_stats():
    return jsonify(get_view_stats())


@bp.route("/saves/stats", methods=["GET"])
def saves_stats():
    return jsonify(get_save_stats())


@bp.route("/clicks/stats", methods=["GET"])
def clicks_stats():
    return jsonify(get_click_stats())
