from flask import Blueprint, jsonify
from app.core.decorators import admin_required

from app.domains.interaction.service import (
    get_all_comments,
    get_interactions_breakdown,
    get_reaction_stats,
    get_view_stats,
    get_save_stats,
    get_share_stats,
    get_click_stats,
    delete_comment as delete_comment_service
)

bp = Blueprint("api_interaction", __name__, url_prefix="/admin/interactions")


# @bp.before_request
# @admin_required
# def require_admin():
#     """Ensure all interactions endpoints require admin privilege."""
#     pass



# ---------------------------
# COMMENTS
# ---------------------------

@bp.route("/comments", methods=["GET"])
def list_comments():
    comments = get_all_comments()

    return jsonify([
        {
            "id": c.id,
            "content": c.content[:100],
            "user_id": c.user_id,
            "parent_id": c.parent_id,
            "sentiment": c.sentiment,
            "target_type": c.target_type,
            "target_id": c.target_id,
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
    """Unified stats endpoint — returns breakdown + total + reaction split."""
    breakdown = get_interactions_breakdown()   # {comments, reactions, views, saves, clicks}
    reaction_stats = get_reaction_stats()      # {likes, dislikes}

    total = sum(breakdown.values())

    return jsonify({
        # Raw breakdown
        "comments":   breakdown.get("comments", 0),
        "reactions":  breakdown.get("reactions", 0),
        "views":      breakdown.get("views", 0),
        "saves":      breakdown.get("saves", 0),
        "shares":     breakdown.get("shares", 0),
        "item_clicks": breakdown.get("clicks", 0),
        # Reaction split
        "likes":      reaction_stats.get("likes", 0),
        "dislikes":   reaction_stats.get("dislikes", 0),
        # Grand total
        "total": total,
    })


@bp.route("/reactions/stats", methods=["GET"])
def reactions_stats():
    return jsonify(get_reaction_stats())


@bp.route("/views/stats", methods=["GET"])
def views_stats():
    return jsonify(get_view_stats())


@bp.route("/saves/stats", methods=["GET"])
def saves_stats():
    return jsonify(get_save_stats())


@bp.route("/shares/stats", methods=["GET"])
def shares_stats():
    return jsonify(get_share_stats())


@bp.route("/clicks/stats", methods=["GET"])
def clicks_stats():
    return jsonify(get_click_stats())
