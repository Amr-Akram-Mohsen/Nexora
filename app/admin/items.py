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
from app.domains.item.models import Item, ItemVariant, ItemStoreLink, Store, ItemImage
from app.domains.taxonomy.models import Category, Brand, Source
from app.admin.helpers import parse_pagination_params, parse_sort_params, make_rows_response
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload
from app.domains.item.models import ItemSpecification
from app.domains.interaction.models import Comment

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


@bp.route("/health_stats", methods=["GET"])
def get_item_health_stats():
    """Return fast KPI stats for the item catalog health dashboard."""
    from datetime import datetime, timezone, timedelta
    
    total_items = db.session.scalar(select(func.count(Item.id))) or 0
    branded_items = db.session.scalar(select(func.count(Item.id)).where(Item.brand_id.isnot(None))) or 0
    
    items_with_images = db.session.scalar(
        select(func.count(func.distinct(ItemImage.item_id)))
    ) or 0
    
    items_with_links = db.session.scalar(
        select(func.count(func.distinct(ItemVariant.item_id)))
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
        .where(ItemStoreLink.is_active.is_(True))
    ) or 0
    
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Items where ALL active store links are stale (last synced > 7 days ago)
    # Actually, simpler: count of items that have NO store links synced in the last 7 days.
    # We can just count items with links, then subtract items with at least one recent sync.
    items_with_recent_sync = db.session.scalar(
        select(func.count(func.distinct(ItemVariant.item_id)))
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
        .where(ItemStoreLink.is_active.is_(True), ItemStoreLink.last_synced_at >= seven_days_ago)
    ) or 0
    stale_sync_items = max(0, items_with_links - items_with_recent_sync)

    # Distribution by item_type
    type_dist_rows = db.session.execute(
        select(Item.item_type, func.count(Item.id))
        .group_by(Item.item_type)
        .order_by(func.count(Item.id).desc())
    ).all()
    
    item_type_distribution = [
        {"type": r[0] or "Uncategorized", "count": r[1]}
        for r in type_dist_rows
    ]

    # Top Items by Engagement (CTR)
    # We define CTR roughly as clicks / views.
    # To avoid division by zero, we filter views > 10.
    top_items_rows = db.session.execute(
        select(
            Item.id, 
            Item.name, 
            Item.click_count, 
            Item.view_count,
            Item.save_count,
            Item.like_count
        )
        .where(Item.view_count > 10)
        .order_by((Item.click_count * 1.0 / Item.view_count).desc())
        .limit(5)
    ).all()
    
    top_engagement_items = []
    for r in top_items_rows:
        ctr = round((r.click_count / r.view_count) * 100, 1) if r.view_count else 0
        save_rate = round((r.save_count / r.view_count) * 100, 1) if r.view_count else 0
        like_rate = round((r.like_count / r.view_count) * 100, 1) if r.view_count else 0
        top_engagement_items.append({
            "id": r.id,
            "name": r.name,
            "ctr": ctr,
            "save_rate": save_rate,
            "like_rate": like_rate
        })

    return jsonify({
        "total_items": total_items,
        "branded_items": branded_items,
        "items_with_images": items_with_images,
        "items_with_links": items_with_links,
        "stale_sync_items": stale_sync_items,
        "item_type_distribution": item_type_distribution,
        "top_engagement_items": top_engagement_items
    })


def _load_item_aggregates(page_ids):
    min_price_rows = db.session.execute(
        select(
            ItemVariant.item_id,
            func.min(ItemVariant.price).label("min_price"),
            func.max(ItemVariant.price).label("max_price"),
            ItemVariant.currency,
        )
        .where(ItemVariant.item_id.in_(page_ids), ItemVariant.price != None)
        .group_by(ItemVariant.item_id, ItemVariant.currency)
        .order_by(ItemVariant.item_id, func.min(ItemVariant.price))
    ).all()

    min_price_map: dict[int, dict] = {}
    for r in min_price_rows:
        if r.item_id not in min_price_map:
            min_price_map[r.item_id] = {
                "price": float(r.min_price), 
                "max_price": float(r.max_price) if r.max_price else None,
                "currency": r.currency
            }

    store_rows = db.session.execute(
        select(
            ItemVariant.item_id,
            func.count(ItemStoreLink.id).label("active_links"),
            func.max(ItemStoreLink.last_synced_at).label("last_synced_at"),
            func.max(ItemStoreLink.old_price).label("max_old_price")
        )
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
        .where(
            ItemVariant.item_id.in_(page_ids),
            ItemStoreLink.is_active.is_(True),
        )
        .group_by(ItemVariant.item_id)
    ).all()

    store_info_map = {
        r.item_id: {
            "active_links": int(r.active_links),
            "last_synced_at": r.last_synced_at,
            "has_discount": r.max_old_price is not None and float(r.max_old_price) > 0
        }
        for r in store_rows
    }
    
    image_rows = db.session.execute(
        select(ItemImage.item_id, func.count(ItemImage.id).label("image_count"))
        .where(ItemImage.item_id.in_(page_ids))
        .group_by(ItemImage.item_id)
    ).all()
    image_info_map = {r.item_id: int(r.image_count) > 0 for r in image_rows}

    spec_rows = db.session.execute(
        select(ItemSpecification.item_id, func.count(ItemSpecification.id).label("spec_count"))
        .where(ItemSpecification.item_id.in_(page_ids))
        .group_by(ItemSpecification.item_id)
    ).all()
    spec_info_map = {r.item_id: int(r.spec_count) > 0 for r in spec_rows}

    return min_price_map, store_info_map, image_info_map, spec_info_map

@bp.route("/", methods=["GET"])
def list_items():
    """Paginated, filterable item listing for the admin control panel."""
    page, per_page = parse_pagination_params(default_per_page=20)
    sort_col, sort_dir = parse_sort_params(_ITEM_SORT_MAP, Item.id)

    search        = request.args.get("search", "").strip()
    brand_slug    = request.args.get("brand")
    category_slug = request.args.get("category")
    source_slug   = request.args.get("source")
    has_images    = request.args.get("has_images")
    has_brand     = request.args.get("has_brand")
    availability  = request.args.get("availability")
    item_type     = request.args.get("item_type")

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
        
    if item_type:
        stmt = stmt.where(Item.item_type == item_type)
        
    if has_images == "true":
        stmt = stmt.where(Item.images.any())
    elif has_images == "false":
        stmt = stmt.where(~Item.images.any())
        
    if has_brand == "true":
        stmt = stmt.where(Item.brand_id.isnot(None))
    elif has_brand == "false":
        stmt = stmt.where(Item.brand_id.is_(None))
        
    if availability and availability != "all":
        # Check if there is any active link with this availability
        stmt = stmt.where(
            Item.variants.any(
                ItemVariant.store_links.any(
                    (ItemStoreLink.is_active == True) & (ItemStoreLink.availability == availability)
                )
            )
        )

    # Note: custom sorting like min_price, store_count, last_synced_at 
    # would need complex joins. We can use subqueries or scalar queries here if we add them.
    # For now we sort on standard fields.
    if sort_col == "min_price":
        # Approximate sort by price subquery
        price_sub = select(func.min(ItemVariant.price)).where(ItemVariant.item_id == Item.id).scalar_subquery()
        stmt = stmt.order_by(price_sub.asc() if sort_dir == "asc" else price_sub.desc())
    elif sort_col == "store_count":
        store_sub = select(func.count(ItemStoreLink.id)).join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id).where(ItemVariant.item_id == Item.id, ItemStoreLink.is_active == True).scalar_subquery()
        stmt = stmt.order_by(store_sub.asc() if sort_dir == "asc" else store_sub.desc())
    else:
        stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    page_ids = [item.id for item in pagination.items]

    min_price_map, store_info_map, image_info_map, spec_info_map = _load_item_aggregates(page_ids)

    serialized = []
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    for item in pagination.items:
        price_info  = min_price_map.get(item.id, {})
        store_info  = store_info_map.get(item.id, {})
        has_image   = image_info_map.get(item.id, False)
        has_specs   = spec_info_map.get(item.id, False)

        # Compute Completeness Score
        completeness_points = 0
        total_criteria = 8
        if has_image: completeness_points += 1
        if item.brand_id: completeness_points += 1
        if item.description and len(item.description) > 10: completeness_points += 1
        if store_info.get("active_links", 0) > 0: completeness_points += 1
        if price_info.get("price") is not None: completeness_points += 1
        if has_specs: completeness_points += 1
        if item.searchable_attributes and len(item.searchable_attributes) > 0: completeness_points += 1
        if item.structured_details and len(item.structured_details) > 0: completeness_points += 1
        
        completeness_score = int((completeness_points / total_criteria) * 100)

        serialized.append({
            "id":          item.id,
            "name":        item.name,
            "slug":        item.slug,
            "image_url":   item.image_url if has_image else None,
            "brand":       item.brand.name if item.brand else "—",
            "brand_slug":  item.brand.slug if item.brand else None,
            "category":    item.category.name if item.category else "—",
            "category_slug": item.category.slug if item.category else None,
            "min_price":   price_info.get("price"),
            "max_price":   price_info.get("max_price"),
            "currency":    price_info.get("currency"),
            "store_count": store_info.get("active_links", 0),
            "last_synced_at": store_info.get("last_synced_at").isoformat() if store_info.get("last_synced_at") else None,
            "has_discount": store_info.get("has_discount", False),
            "health":      completeness_score,
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
    has_images    = request.args.get("has_images")
    has_brand     = request.args.get("has_brand")
    availability  = request.args.get("availability")
    item_type     = request.args.get("item_type")

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
    if item_type:
        stmt = stmt.where(Item.item_type == item_type)
    if has_images == "true":
        stmt = stmt.where(Item.images.any())
    elif has_images == "false":
        stmt = stmt.where(~Item.images.any())
    if has_brand == "true":
        stmt = stmt.where(Item.brand_id.isnot(None))
    elif has_brand == "false":
        stmt = stmt.where(Item.brand_id.is_(None))
    if availability and availability != "all":
        stmt = stmt.where(
            Item.variants.any(
                ItemVariant.store_links.any(
                    (ItemStoreLink.is_active == True) & (ItemStoreLink.availability == availability)
                )
            )
        )

    if sort_col == "min_price":
        price_sub = select(func.min(ItemVariant.price)).where(ItemVariant.item_id == Item.id).scalar_subquery()
        stmt = stmt.order_by(price_sub.asc() if sort_dir == "asc" else price_sub.desc())
    elif sort_col == "store_count":
        store_sub = select(func.count(ItemStoreLink.id)).join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id).where(ItemVariant.item_id == Item.id, ItemStoreLink.is_active == True).scalar_subquery()
        stmt = stmt.order_by(store_sub.asc() if sort_dir == "asc" else store_sub.desc())
    elif sort_col == "last_synced_at":
        sync_sub = select(func.max(ItemStoreLink.last_synced_at)).join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id).where(ItemVariant.item_id == Item.id).scalar_subquery()
        stmt = stmt.order_by(sync_sub.asc() if sort_dir == "asc" else sync_sub.desc())
    else:
        stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    page_ids = [item.id for item in pagination.items]

    min_price_map, store_info_map, image_info_map, spec_info_map = _load_item_aggregates(page_ids)

    serialized = []
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    for item in pagination.items:
        price_info = min_price_map.get(item.id, {})
        store_info = store_info_map.get(item.id, {})
        has_image = image_info_map.get(item.id, False)
        has_specs = spec_info_map.get(item.id, False)
        
        price_str = f'{price_info.get("price")} {price_info.get("currency")}'
        if price_info.get("max_price") and price_info.get("max_price") > price_info.get("price"):
            price_str = f'{price_info.get("price")} – {price_info.get("max_price")} {price_info.get("currency")}'

        # Compute sync age
        sync_age_days = None
        last_synced_at = store_info.get("last_synced_at")
        if last_synced_at:
            if last_synced_at.tzinfo is None:
                last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)
            sync_age_days = (now - last_synced_at).days

        # Compute Completeness Score
        completeness_points = 0
        total_criteria = 8
        if has_image: completeness_points += 1
        if item.brand_id: completeness_points += 1
        if item.description and len(item.description) > 10: completeness_points += 1
        if store_info.get("active_links", 0) > 0: completeness_points += 1
        if price_info.get("price") is not None: completeness_points += 1
        if has_specs: completeness_points += 1
        if item.searchable_attributes and len(item.searchable_attributes) > 0: completeness_points += 1
        if item.structured_details and len(item.structured_details) > 0: completeness_points += 1
        
        completeness_score = int((completeness_points / total_criteria) * 100)

        serialized.append({
            "id":          item.id,
            "name":        item.name,
            "image_url":   item.image_url if has_image else None,
            "taxonomy":    f'{item.category.name} / {item.brand.name}' if item.brand else item.category.name,
            "price":       price_str,
            "store-count": store_info.get("active_links", 0),
            "sync-age":    sync_age_days,
            "has-discount": store_info.get("has_discount", False),
            "health":      completeness_score,
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
                "old_price":         float(lnk.old_price) if lnk.old_price is not None else None,
                "currency":          lnk.currency,
                "availability":      lnk.availability,
                "is_active":         lnk.is_active,
                "last_synced_at":    lnk.last_synced_at.isoformat() if lnk.last_synced_at else None,
                "last_checked_at":   lnk.last_checked_at.isoformat() if lnk.last_checked_at else None,
                "merchant_category": lnk.merchant_category or "—",
                "external_item_id":  lnk.external_item_id or "—",
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
        "description": f"{item.description[:200]}..." if item.description and len(item.description) > 200 else (item.description or "No"),
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
        
    variant_summary = []
    for v in item.variants:
        variant_summary.append({
            "id": v.id,
            "sku": v.sku,
            "is_default": v.is_default,
            "attributes": v.attributes,
            "price": float(v.price) if v.price is not None else None,
            "old_price": float(v.old_price) if v.old_price is not None else None,
            "currency": v.currency,
            "store_links_count": len(v.store_links),
            "images_count": len(v.images)
        })

    image_strip = []
    for img in item.images:
        image_strip.append({
            "id": img.id,
            "url": img.image_url,
            "is_primary": img.position == 0,
            "variant_id": img.variant_id,
            "position": img.position
        })

    specifications = {
        "structured_details": item.structured_details,
        "quick_details": item.quick_details,
        "searchable_attributes": item.searchable_attributes,
        "specs_list": [{"key": s.category, "value": s.spec_json} for s in item.specifications]
    }

    return {
        "inspect_table": inspect_table,
        "store_links": store_links_data,
        "variant_summary": variant_summary,
        "image_strip": image_strip,
        "specifications": specifications,
        "distribution_history": distribution_history,
        "actions": actions,
        "inspect_id": item.id
    }

