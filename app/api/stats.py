from flask import Blueprint, jsonify
from app.domains.article.service.query import count_articles
from app.domains.item.service.query import count_items
from app.domains.user.service.query import count_users
from app.domains.interaction.service.query import count_interactions

bp = Blueprint("api_dashboard", __name__, url_prefix="/api/dashboard")

@bp.route("/stats", methods=["GET"])
def dashboard_stats():
    return jsonify({
        "articles_count": count_articles(),
        "items_count": count_items(),
        "users_count": count_users(),
        "interactions": count_interactions()
    })
