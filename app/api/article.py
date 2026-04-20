from flask import Blueprint, jsonify, request
from app.domains.article.service import get_articles  # adjust if needed

bp = Blueprint("api_article", __name__, url_prefix="/api/articles")


@bp.route("/", methods=["GET"])
def list_articles():
    articles = get_articles()  # your query function

    # TEMP FIX: convert to simple JSON
    return jsonify([
        {
            "id": a.id,
            "title": a.title,
            "published_at": a.published_at,
            "view_count": a.view_count,
        }
        for a in articles
    ])

@bp.route("/<id>", methods=["DELETE"])
def delete_article(id):
    from app.core.extensions import db
    from app.domains.article.models import Article
    article = db.session.get(Article, id)
    if not article:
        return jsonify({"error": "Article not found"}), 404
    
    db.session.delete(article)
    db.session.commit()
    return jsonify({"success": True}), 200
