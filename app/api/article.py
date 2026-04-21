from flask import Blueprint, jsonify, request
from app.domains.article.service import get_articles  # adjust if needed

bp = Blueprint("api_article", __name__, url_prefix="/api/articles")


@bp.route("/", methods=["GET"])
def list_articles():
    search = request.args.get('search')
    source = request.args.get('source')
    articles = get_articles(search=search, source=source)  # your query function

    # TEMP FIX: convert to simple JSON
    return jsonify([
        {
            "id": a.id,
            "title": a.title,
            "published_at": str(a.published_at) if a.published_at else None,
            "view_count": a.view_count,
        }
        for a in articles
    ])

@bp.route("/<int:id>", methods=["DELETE"])
# TODO: Add authentication/authorization decorator (e.g., @admin_required)
def delete_article(id):
    from app.core.extensions import db
    from app.domains.article.models import Article
    article = db.session.get(Article, id)
    if not article:
        return jsonify({"error": "Article not found"}), 404
    
    db.session.delete(article)
    db.session.commit()
    return jsonify({"success": True}), 200
