from flask import Blueprint, jsonify, request
from app.domains.content.service import get_contents, delete_content as delete_content_service
from app.core.decorators import admin_required

bp = Blueprint("api_content", __name__, url_prefix="/api/contents")


@bp.route("/", methods=["GET"])
def list_contents():
    search = request.args.get('search')
    source = request.args.get('source')
    contents = get_contents(search=search, source=source)

    return jsonify([
        {
            "id": a.id,
            "title": a.object_type,
            "published_at": str(a.published_at) if a.published_at else None,
            "view_count": a.view_count,
        }
        for a in contents
    ])

@bp.route("/<int:id>", methods=["DELETE"])
@admin_required
def delete_content(id):
    success = delete_content_service(id)

    if not success:
        return jsonify({"error": "Article not found"}), 404
    
    return jsonify({"success": True}), 200
