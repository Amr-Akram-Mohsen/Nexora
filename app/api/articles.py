from flask import Blueprint, jsonify, request
from app.domains.article.service import get_articles, delete_article as delete_article_service
from app.core.decorators import admin_required

bp = Blueprint("api_article", __name__, url_prefix="/api/articles")


@bp.route("/", methods=["GET"])
def list_articles():
    search = request.args.get('search')
    source = request.args.get('source')
    articles = get_articles(search=search, source=source)

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
@admin_required
def delete_article(id):
    success = delete_article_service(id)

    if not success:
        return jsonify({"error": "Article not found"}), 404
    
    return jsonify({"success": True}), 200
