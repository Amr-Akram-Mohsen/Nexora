from flask import Blueprint, jsonify, request
from app.domains.item.service import get_items, delete_item as delete_item_service
from app.core.decorators import admin_required
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
@admin_required
def delete_item(id):
    success = delete_item_service(id)

    if not success:
        return jsonify({"error": "Item not found"}), 404

    return jsonify({"success": True})
