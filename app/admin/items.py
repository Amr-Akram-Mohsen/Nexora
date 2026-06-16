# app/admin/items.py
"""
Admin item management endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- store_links removed from listing serialization; new /admin/items/<id>/detail
  endpoint serves the inspect modal (R-14).
- min_price and store_count computed via SQL subqueries instead of ORM
  relationship traversal during serialization (R-15).
- Shared helpers from app.admin.helpers for pagination and sort parsing (R-18, R-21).
"""
from flask import Blueprint, jsonify, request, render_template, make_response
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.item.models import Item, ItemVariant, ItemStoreLink, Store
from app.domains.taxonomy.models import Category, Brand, Source
from app.admin.helpers import parse_pagination_params, parse_sort_params
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload

bp = Blueprint("api_item", __name__, url_prefix="/admin/items")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all item management endpoints require admin privilege."""
    pass


# ─────────────────────────────────────────────
# SORT MAP
# ─────────────────────────────────────────────

_ITEM_SORT_MAP = {
    "id":          Item.id,
    "created_at":  Item.created_at,
    "name":        Item.name,
    "click_count": Item.click_count,
    "view_count":  Item.view_count,
}


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@bp.route("/meta", methods=["GET"])
def get_item_meta():
    """Return brands, categories, and sources for dropdown filters."""
    categories = db.session.execute(
        select(Category.id, Category.name, Category.slug)
        .where(Category.id.in_(select(Item.category_id).distinct()))
        .order_by(Category.name)
    ).mappings().all()

    brands = db.session.execute(
        select(Brand.id, Brand.name, Brand.slug)
        .where(Brand.id.in_(select(Item.brand_id).distinct()))
        .order_by(Brand.name)
    ).mappings().all()

    item_types = db.session.execute(
        select(Item.item_type).distinct().order_by(Item.item_type)
    ).scalars().all()

    sources = db.session.execute(
        select(Source.id, Source.name, Source.slug)
        .where(Source.id.in_(select(Item.source_id).distinct()))
        .order_by(Source.name)
    ).mappings().all()

    return jsonify({
        "categories": [dict(r) for r in categories],
        "brands":     [dict(r) for r in brands],
        "item_types": [t for t in item_types if t],
        "sources":    [dict(r) for r in sources],
    })


@bp.route("/", methods=["GET"])
def list_items():
    """Paginated, filterable item listing for the admin control panel."""
    page, per_page = parse_pagination_params(default_per_page=20)
    sort_col, sort_dir = parse_sort_params(_ITEM_SORT_MAP, Item.id)

    search        = request.args.get("search", "").strip()
    brand_slug    = request.args.get("brand")
    category_slug = request.args.get("category")
    source_slug   = request.args.get("source")

    # ── Build base query with SQL subqueries for aggregated fields (R-15) ─
    # min_price subquery: lowest price across all variants for each item
    min_price_sq = (
        select(func.min(ItemVariant.price), ItemVariant.currency)
        .where(ItemVariant.item_id == Item.id)
        .order_by(func.min(ItemVariant.price))
        .limit(1)
        .correlate(Item)
        .scalar_subquery()
    )

    # store_count subquery: number of active store links across all variants
    store_count_sq = (
        select(func.count(ItemStoreLink.id))
        .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
        .where(ItemVariant.item_id == Item.id, ItemStoreLink.is_active == True)
        .correlate(Item)
        .scalar_subquery()
    )

    stmt = select(Item).options(joinedload(Item.brand), joinedload(Item.category))

    if search:
        term = f"%{search}%"
        if search.isdigit():
            stmt = stmt.where(or_(Item.id == int(search), Item.name.ilike(term)))
        else:
            stmt = stmt.where(or_(Item.name.ilike(term), Item.description.ilike(term)))

    if brand_slug:
        stmt = stmt.join(Item.brand).where(Brand.slug == brand_slug)

    if category_slug:
        stmt = stmt.join(Item.category).where(Category.slug == category_slug)

    if source_slug:
        stmt = stmt.join(Item.source).where(Source.slug == source_slug)

    stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    # ── Compute aggregated values for this page in bulk (R-15) ────────────
    page_ids = [item.id for item in pagination.items]

    # Fetch min price per item
    min_price_rows = db.session.execute(
        select(
            ItemVariant.item_id,
            func.min(ItemVariant.price).label("min_price"),
            ItemVariant.currency,
        )
        .where(ItemVariant.item_id.in_(page_ids), ItemVariant.price != None)
        .group_by(ItemVariant.item_id, ItemVariant.currency)
        .order_by(ItemVariant.item_id, func.min(ItemVariant.price))
    ).all()

    # Keep only the lowest per item_id (in case of multi-currency)
    min_price_map: dict[int, dict] = {}
    for r in min_price_rows:
        if r.item_id not in min_price_map:
            min_price_map[r.item_id] = {"price": float(r.min_price), "currency": r.currency}

    # Fetch active store link counts per item
    # store_count_rows = db.session.execute(
    #     select(
    #         ItemVariant.item_id,
    #         func.count(ItemStoreLink.id).label("active_links"),
    #     )
    #     .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
    #     .where(ItemVariant.item_id.in_(page_ids), ItemStoreLink.is_active == True)
    #     .group_by(ItemVariant.item_id)
    # ).all()

    # Fetch active store link counts per item
    store_rows = db.session.execute(
        select(
            ItemVariant.item_id,
            func.count(ItemStoreLink.id).label("active_links"),
        )
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
        .where(
            ItemVariant.item_id.in_(page_ids),
            ItemStoreLink.is_active.is_(True),
        )
        .group_by(ItemVariant.item_id)
    ).all()

    store_info_map: dict[int, dict] = {
        r.item_id: {
            "active_links": int(r.active_links),
        }
        for r in store_rows
    }

    # ── Serialize (no ORM relationship traversal needed for list view) ────
    serialized = []
    for item in pagination.items:
        price_info  = min_price_map.get(item.id, {})
        store_info  = store_info_map.get(item.id, {})
        store_count = store_info.get("active_links", 0)

        serialized.append({
            "id":          item.id,
            "name":        item.name,
            "slug":        item.slug,
            "brand":       item.brand.name if item.brand else "—",
            "brand_slug":  item.brand.slug if item.brand else None,
            "category":    item.category.name if item.category else "—",
            "category_slug": item.category.slug if item.category else None,
            "min_price":   price_info.get("price"),
            "currency":    price_info.get("currency"),
            "store_count": store_count,
            "click_count": item.click_count or 0,
            "view_count":  item.view_count or 0,
            "created_at":  item.created_at.isoformat() if item.created_at else None,
        })

    return jsonify({
        "items":    serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/<int:id>/detail", methods=["GET"])
def get_item_detail(id):
    """
    Return full variant and store-link details for a single item.
    Used by the admin inspect modal (replaces embedding store_links in
    every listing row).
    """
    item = db.session.get(Item, id)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    store_links_data = []
    for v in item.variants:
        for lnk in v.store_links:
            store_links_data.append({
                "store_name":        lnk.store.name if lnk.store else "—",
                "affiliate_network": lnk.store.affiliate_network if lnk.store else "—",
                "program_name":      lnk.program_name or "—",
                "affiliate_url":     lnk.affiliate_url or "—",
                "original_url":      lnk.original_url or "—",
                "price":             float(lnk.price) if lnk.price is not None else None,
                "currency":          lnk.currency,
                "availability":      lnk.availability,
                "is_active":         lnk.is_active,
                "metadata":          lnk.network_metadata or {},
            })

    return jsonify({
        "id":          item.id,
        "name":        item.name,
        "item_type":   item.item_type or "—",
        "brand":       item.brand.name if item.brand else "—",
        "category":    item.category.name if item.category else "—",
        "source_name": item.source.name if item.source else "—",
        "source_slug": item.source.slug if item.source else None,
        "source_type": item.source_type or "—",
        "store_links": store_links_data,
    })


@bp.route("/<int:id>", methods=["DELETE"])
def delete_item(id):
    """Delete an item and all its variants, store links, and images."""
    item = db.session.get(Item, id)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True, "message": f"Item '{item.name}' deleted successfully."})


@bp.route("/rows", methods=["GET"])
def items_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=20)
    sort_col, sort_dir = parse_sort_params(_ITEM_SORT_MAP, Item.id)

    search        = request.args.get("search", "").strip()
    brand_slug    = request.args.get("brand")
    category_slug = request.args.get("category")
    source_slug   = request.args.get("source")

    stmt = select(Item).options(joinedload(Item.brand), joinedload(Item.category))
    if search:
        term = f"%{search}%"
        if search.isdigit():
            stmt = stmt.where(or_(Item.id == int(search), Item.name.ilike(term)))
        else:
            stmt = stmt.where(or_(Item.name.ilike(term), Item.description.ilike(term)))
    if brand_slug:
        stmt = stmt.join(Item.brand).where(Brand.slug == brand_slug)
    if category_slug:
        stmt = stmt.join(Item.category).where(Category.slug == category_slug)
    if source_slug:
        stmt = stmt.join(Item.source).where(Source.slug == source_slug)
    stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    page_ids = [item.id for item in pagination.items]

    min_price_rows = db.session.execute(
        select(ItemVariant.item_id, func.min(ItemVariant.price).label("min_price"), ItemVariant.currency)
        .where(ItemVariant.item_id.in_(page_ids), ItemVariant.price != None)
        .group_by(ItemVariant.item_id, ItemVariant.currency)
        .order_by(ItemVariant.item_id, func.min(ItemVariant.price))
    ).all()
    min_price_map: dict[int, dict] = {}
    for r in min_price_rows:
        if r.item_id not in min_price_map:
            min_price_map[r.item_id] = {"price": float(r.min_price), "currency": r.currency}

    store_rows = db.session.execute(
        select(ItemVariant.item_id, func.count(ItemStoreLink.id).label("active_links"))
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
        .where(ItemVariant.item_id.in_(page_ids), ItemStoreLink.is_active.is_(True))
        .group_by(ItemVariant.item_id)
    ).all()
    store_info_map = {r.item_id: int(r.active_links) for r in store_rows}

    serialized = []
    for item in pagination.items:
        price_info = min_price_map.get(item.id, {})
        serialized.append({
            "id":          item.id,
            "name":        item.name,
            "brand":       item.brand.name if item.brand else "—",
            "category":    item.category.name if item.category else "—",
            "min_price":   price_info.get("price"),
            "currency":    price_info.get("currency"),
            "store_count": store_info_map.get(item.id, 0),
            "click_count": item.click_count or 0,
            "created_at":  item.created_at.isoformat() if item.created_at else None,
        })

    html = render_template("admin/control_panel/items/_rows.html", items=serialized)
    resp = make_response(html)
    resp.headers["X-Total"] = pagination.total
    resp.headers["X-Pages"] = pagination.pages
    resp.headers["X-Page"]  = pagination.page
    return resp


@bp.route("/<int:id>/inspect", methods=["GET"])
def inspect_item(id):
    """Return server-rendered HTML for the item inspect modal body."""
    item = db.session.get(Item, id)
    if not item:
        return "<p class='text-muted'>Item not found.</p>", 404

    store_links_data = []
    for v in item.variants:
        for lnk in v.store_links:
            store_links_data.append({
                "store_name":        lnk.store.name if lnk.store else "—",
                "affiliate_network": lnk.store.affiliate_network if lnk.store else "—",
                "program_name":      lnk.program_name or "—",
                "affiliate_url":     lnk.affiliate_url or "—",
                "original_url":      lnk.original_url or "—",
                "price":             float(lnk.price) if lnk.price is not None else None,
                "currency":          lnk.currency,
                "availability":      lnk.availability,
                "is_active":         lnk.is_active,
                "metadata":          lnk.network_metadata or {},
            })

    data = {
        "id":          item.id,
        "name":        item.name,
        "item_type":   item.item_type or "—",
        "brand":       item.brand.name if item.brand else "—",
        "category":    item.category.name if item.category else "—",
        "source_name": item.source.name if item.source else "—",
        "source_slug": item.source.slug if item.source else None,
        "source_type": item.source_type or "—",
        "store_links": store_links_data,
    }
    return render_template("admin/control_panel/items/_inspect.html", item=data)

