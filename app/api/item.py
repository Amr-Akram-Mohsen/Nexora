from flask import Blueprint, jsonify, request
from app.domains.item.service.query import get_items

bp = Blueprint("api_item", __name__, url_prefix="/api/items")


@bp.route("/", methods=["GET"])
def list_items():
    search = request.args.get('search')
    brand = request.args.get('brand')
    items = get_items(search=search, brand=brand)

    return jsonify([
        {
            "id": i.id,
            "name": i.name,
            "rating": i.rating,
            "created_at": str(i.created_at)
        }
        for i in items
    ])


@bp.route("/<int:id>", methods=["DELETE"])
# TODO: Add authentication/authorization decorator (e.g., @admin_required)
def delete_item(id):
    from app.core.extensions import db
    from app.domains.item.models import Item

    item = db.session.get(Item, id)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({"success": True})
