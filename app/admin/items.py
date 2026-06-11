# app/admin/items.py
from flask import Blueprint, jsonify, request
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.item.models import Item, ItemVariant, ItemStoreLink
from app.domains.taxonomy.models import Category, Brand
from sqlalchemy import select, func, or_

bp = Blueprint("api_item", __name__, url_prefix="/admin/items")


@bp.route("/meta", methods=["GET"])
def get_item_meta():
    """Return brands and categories for dropdown filters."""
    categories = db.session.execute(
        select(Category.id, Category.name, Category.slug).order_by(Category.name)
    ).mappings().all()
    brands = db.session.execute(
        select(Brand.id, Brand.name, Brand.slug).order_by(Brand.name)
    ).mappings().all()
    item_types = db.session.execute(
        select(Item.item_type).distinct().order_by(Item.id)
    ).scalars().all()

    return jsonify({
        "categories": [dict(r) for r in categories],
        "brands": [dict(r) for r in brands],
        "item_types": [t for t in item_types if t],
    })


@bp.route("/", methods=["GET"])
def list_items():
    """Paginated, filterable item listing for the admin control panel."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    sort_by = request.args.get("sort_by", "id")
    sort_dir = request.args.get("sort_dir", "desc")
    search = request.args.get("search", "").strip()
    brand_slug = request.args.get("brand")
    category_slug = request.args.get("category")
    item_type = request.args.get("item_type")

    stmt = select(Item)

    if search:
        search_term = f"%{search}%"
        if search.isdigit():
            stmt = stmt.where(or_(Item.id == int(search), Item.name.ilike(search_term)))
        else:
            stmt = stmt.where(or_(Item.name.ilike(search_term), Item.description.ilike(search_term)))

    if brand_slug:
        stmt = stmt.join(Item.brand).where(Brand.slug == brand_slug)

    if category_slug:
        stmt = stmt.join(Item.category).where(Category.slug == category_slug)

    if item_type:
        stmt = stmt.where(Item.item_type == item_type)

    # Sorting
    sort_col_map = {
        "id": Item.id,
        "created_at": Item.created_at,
        "name": Item.name,
        "rating": Item.rating,
        "click_count": Item.click_count,
        "view_count": Item.view_count,
    }
    sort_col = sort_col_map.get(sort_by, Item.id)
    stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    serialized = []
    for item in pagination.items:
        # Count active store links via subquery (already eager-loaded via selectin on variants)
        store_count = sum(
            1 for v in item.variants for lnk in v.store_links if lnk.is_active
        )
        # Get min price from default variant or first variant
        min_price = None
        currency = None
        for v in item.variants:
            if v.price is not None:
                price_val = float(v.price)
                if min_price is None or price_val < min_price:
                    min_price = price_val
                    currency = v.currency

        serialized.append({
            "id": item.id,
            "name": item.name,
            "slug": item.slug,
            "item_type": item.item_type or "—",
            "brand": item.brand.name if item.brand else "—",
            "brand_slug": item.brand.slug if item.brand else None,
            "category": item.category.name if item.category else "—",
            "category_slug": item.category.slug if item.category else None,
            "rating": item.rating,
            "min_price": min_price,
            "currency": currency,
            "store_count": store_count,
            "click_count": item.click_count or 0,
            "view_count": item.view_count or 0,
            "source_type": item.source_type or "—",
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return jsonify({
        "items": serialized,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/<int:id>", methods=["DELETE"])
@admin_required
def delete_item(id):
    """Delete an item and all its variants, store links, and images."""
    item = db.session.get(Item, id)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True, "message": f"Item '{item.name}' deleted successfully."})
