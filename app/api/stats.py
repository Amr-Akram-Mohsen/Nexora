from flask import Blueprint, jsonify
from app.domains.article.service.query import count_articles
from app.domains.item.service.query import count_items
from app.domains.user.service.query import count_users
from app.domains.interaction.service.query import get_interactions_breakdown, get_reaction_stats

bp = Blueprint("api_dashboard", __name__, url_prefix="/api/dashboard")

@bp.route("/stats", methods=["GET"])
def dashboard_stats():
    breakdown = get_interactions_breakdown()   # {comments, reactions, views, saves, clicks}
    reaction_stats = get_reaction_stats()      # {likes, dislikes}
    total = sum(breakdown.values())

    return jsonify({
        "articles_count": count_articles(),
        "items_count": count_items(),
        "users_count": count_users(),
        "interactions": {
            "total":     total,
            "views":     breakdown.get("views", 0),
            "comments":  breakdown.get("comments", 0),
            "reactions": breakdown.get("reactions", 0),
            "saves":     breakdown.get("saves", 0),
            "clicks":    breakdown.get("clicks", 0),
            "likes":     reaction_stats.get("likes", 0),
            "dislikes":  reaction_stats.get("dislikes", 0),
        }
    })
