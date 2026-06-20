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
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.item.models import Item, ItemVariant, ItemStoreLink, Store
from app.domains.taxonomy.models import Category, Brand, Source
from app.admin.helpers import parse_pagination_params, parse_sort_params, make_rows_response
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


def _load_item_aggregates(page_ids):
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

    min_price_map: dict[int, dict] = {}
    for r in min_price_rows:
        if r.item_id not in min_price_map:
            min_price_map[r.item_id] = {"price": float(r.min_price), "currency": r.currency}

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

    store_info_map = {r.item_id: int(r.active_links) for r in store_rows}
    return min_price_map, store_info_map

@bp.route("/", methods=["GET"])
def list_items():
    """Paginated, filterable item listing for the admin control panel."""
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

    min_price_map, store_info_map = _load_item_aggregates(page_ids)

    serialized = []
    for item in pagination.items:
        price_info  = min_price_map.get(item.id, {})
        store_count = store_info_map.get(item.id, 0)

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

    min_price_map, store_info_map = _load_item_aggregates(page_ids)

    serialized = []
    for item in pagination.items:
        price_info = min_price_map.get(item.id, {})
        serialized.append({
            "id":          item.id,
            "name":        item.name,
            "taxonomy": f'{item.category.name} / {item.brand.name}',
            "price":   f'{price_info.get("price")} {price_info.get("currency")}',
            "store-count": store_info_map.get(item.id, 0),
            "click-count": item.click_count or 0,
            "created-at":  item.created_at.isoformat() if item.created_at else None,
        })

    html = render_template("admin/components/_rows.html", items=serialized, domain_type='item')
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


def build_item_inspect_data(id):
    """Return dictionary of data needed for the item inspect/detail view."""
    from sqlalchemy.orm import selectinload, joinedload
    item = db.session.scalar(
        select(Item).options(
            joinedload(Item.category),
            joinedload(Item.brand),
            joinedload(Item.source),
            selectinload(Item.variants).selectinload(ItemVariant.store_links).joinedload(ItemStoreLink.store),
            selectinload(Item.linked_contents),
            selectinload(Item.images),
            selectinload(Item.specifications),
            selectinload(Item.comments).joinedload(Comment.user)
        ).where(Item.id == id)
    )
    
    if not item:
        return None

    store_links_data = []
    last_synced_dates = []
    
    for v in item.variants:
        for lnk in v.store_links:
            if lnk.last_synced_at:
                last_synced_dates.append(lnk.last_synced_at)
            elif lnk.last_checked_at:
                last_synced_dates.append(lnk.last_checked_at)
                
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
                "commission_rate":   float(lnk.commission_rate) if lnk.commission_rate is not None else None,
            })

    last_synced = max(last_synced_dates) if last_synced_dates else None

    from app.admin.helpers import format_date
    from app.admin.tables import get_inspect_table
    
    variant_groups_str = "—"
    if item.variant_groups:
        variant_groups_str = ", ".join(f"<b>{k.title()}</b>: {', '.join(v)}" for k, v in item.variant_groups.items())

    price_str = "—"
    if item.min_price is not None and store_links_data:
        curr = store_links_data[0]["currency"] if store_links_data else ""
        price_str = f"{item.min_price} {curr}"

    from app.domains.interaction.service.scoring import get_item_engagement_score
    engagement_score = get_item_engagement_score(item.id)

    data = {
        "id": f"#{item.id}",
        "name": item.name,
        "category": item.category.name if item.category else "—",
        "brand": item.brand.name if item.brand else "—",
        "source": item.source.name if item.source else "—",
        "added": format_date(item.created_at, fmt='%b %d, %Y') if item.created_at else "—",
        "last synced": format_date(last_synced, fmt='%b %d, %Y') if last_synced else "—",
        "variants count": "{:,}".format(len(item.variants)),
        "store count": "{:,}".format(len(store_links_data)),
        "price": price_str,
        "variant groups": {"value": variant_groups_str, "is_custom": True},
        
        "engagement score": str(engagement_score),
        "views": "{:,}".format(item.view_count or 0),
        "likes": "{:,}".format(item.like_count or 0),
        "dislikes": "{:,}".format(item.dislike_count or 0),
        "comments": "{:,}".format(item.comment_count or 0),
        "shares": "{:,}".format(item.share_count or 0),
        "saves": "{:,}".format(item.save_count or 0),
        "click count": "{:,}".format(item.click_count or 0),
        
        "linked contents": "{:,}".format(len(item.linked_contents)),
        "description": "Yes" if item.description else "No",
        "rating": str(item.rating) if item.rating is not None else "—",
        "review count": "{:,}".format(item.review_count or 0),
        "images count": "{:,}".format(len(item.images)),
        "specs count": "{:,}".format(len(item.specifications)),
    }
    
    inspect_table = get_inspect_table("items", data)

    from datetime import datetime
    recent_comments = sorted(item.comments, key=lambda c: c.created_at or datetime.min, reverse=True)[:3]
    if recent_comments:
        if "Content & Quality" not in inspect_table:
            inspect_table["Content & Quality"] = []
        for idx, c in enumerate(recent_comments):
            user_name = c.user.name if c.user else f"User #{c.user_id}"
            preview = c.content[:100] + ("..." if len(c.content) > 100 else "")
            inspect_table["Content & Quality"].append({
                "label": f"Recent Comment {idx+1}",
                "value": f"<b>{user_name}</b>: {preview}",
                "is_custom": True
            })

    actions = [
        {
            "label": "Delete Product",
            "action_type": "delete",
            "icon": "🗑",
            "extra_class": "user-action-delete",
            "attrs": {"data-action": "delete-item", "data-id": item.id, "data-name": item.name}
        }
    ]

    from app.domains.distribution.services import get_distribution_history
    distribution_history = get_distribution_history("item", id)
        
    return {
        "inspect_table": inspect_table,
        "store_links": store_links_data,
        "distribution_history": distribution_history,
        "actions": actions,
        "inspect_id": item.id
    }

