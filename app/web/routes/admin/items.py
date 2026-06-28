# app/admin/items.py
"""
Admin item management endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- store_links removed from listing serialization; new /admin/items/<id>/detail
  endpoint serves the inspect modal (R-14).
- min_price and store_count computed via SQL subqueries instead of ORM
  relationship traversal during serialization (R-15).
- Shared helpers from app.web.routes.admin.helpers for pagination and sort parsing (R-18, R-21).
"""
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.item.models import Item, ItemVariant, ItemStoreLink, Store, ItemImage
from app.domains.taxonomy.models import Category, Brand, Source
from app.web.routes.admin.helpers import parse_pagination_params, parse_sort_params, make_rows_response
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload
from app.domains.item.models import ItemSpecification
from app.domains.interaction.models import Comment
from app.domains.analytics import get_catalog_health_report
from app.domains.item.service.admin import (
    get_admin_item_meta,
    get_admin_item_health_stats,
    load_admin_item_aggregates,
    build_admin_items_query,
    get_admin_item_inspect_raw,
    get_admin_items_page,
    get_admin_item
)
from app.application.item.admin import delete_item_workflow

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
    return jsonify(get_admin_item_meta())


@bp.route("/health_stats", methods=["GET"])
def get_item_health_stats():
    """Return fast KPI stats for the item catalog health dashboard."""
    return jsonify(get_admin_item_health_stats())

@bp.route("/catalog-health", methods=["GET"])
def catalog_health():
    """Renders the full Catalog Health Dashboard."""
    data = get_catalog_health_report()
    return render_template("admin/items/catalog_health.html", data=data)

@bp.route("/", methods=["GET"])
def list_items():
    """Paginated, filterable item listing for the admin control panel."""
    page, per_page = parse_pagination_params(default_per_page=20)
    sort_col, sort_dir = parse_sort_params(_ITEM_SORT_MAP, Item.id)

    pagination = get_admin_items_page(request.args, sort_col, sort_dir, page, per_page)
    page_ids = [item.id for item in pagination.items]

    min_price_map, store_info_map, image_info_map, spec_info_map = load_admin_item_aggregates(page_ids)

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
    item = get_admin_item(id)
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

    prices = [p["price"] for p in store_links_data if p["price"] is not None and p["is_active"]]
    price_spread = None
    if prices:
        min_p = min(prices)
        max_p = max(prices)
        delta_pct = ((max_p - min_p) / min_p * 100) if min_p > 0 else 0
        price_spread = {
            "min": round(min_p, 2),
            "max": round(max_p, 2),
            "delta_percentage": round(delta_pct, 1)
        }

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
        "price_spread": price_spread
    })


@bp.route("/<int:id>", methods=["DELETE"])
def delete_item(id):
    """Delete an item and all its variants, store links, and images."""
    deleted_name = delete_item_workflow(id)
    if not deleted_name:
        return jsonify({"error": "Item not found"}), 404

    return jsonify({"success": True, "message": f"Item '{deleted_name}' deleted successfully."})


@bp.route("/rows", methods=["GET"])
def items_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=20)
    sort_col, sort_dir = parse_sort_params(_ITEM_SORT_MAP, Item.id)

    pagination = get_admin_items_page(request.args, sort_col, sort_dir, page, per_page)
    page_ids = [item.id for item in pagination.items]

    min_price_map, store_info_map, image_info_map, spec_info_map = load_admin_item_aggregates(page_ids)

    serialized = []
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    for item in pagination.items:
        price_info = min_price_map.get(item.id, {})
        store_info = store_info_map.get(item.id, {})
        has_image = image_info_map.get(item.id, False)
        has_specs = spec_info_map.get(item.id, False)
        
        price_min = price_info.get("price")
        price_max = price_info.get("max_price")
        currency = price_info.get("currency")

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
            "category_name": item.category.name if item.category else None,
            "brand_name":  item.brand.name if item.brand else None,
            "min_price":   price_min,
            "max_price":   price_max,
            "currency":    currency,
            "store_count": store_info.get("active_links", 0),
            "sync_age":    sync_age_days,
            "has_discount": store_info.get("has_discount", False),
            "health":      completeness_score,
            "click_count": item.click_count or 0,
            "created_at":  item.created_at.isoformat() if item.created_at else None,
        })

    html = render_template("admin/components/_rows.html", items=serialized, domain_type='item')
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


@bp.route("/<int:id>/inspect", methods=["GET"])
def inspect_item(id):
    data = build_item_inspect_data(id)
    if not data:
        return jsonify({"error": "Item not found"}), 404
    data["domain"] = "items"
    return render_template("admin/components/_inspect.html", **data)


def build_item_inspect_data(id):
    """Return dictionary of data needed for the item inspect/detail view."""
    item = get_admin_item_inspect_raw(id)
    
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

    from app.web.routes.admin.helpers import format_date
    from app.web.routes.admin.tables import get_inspect_table
    
    variant_groups = [{"label": k.title(), "detail": ", ".join(v)} for k, v in item.variant_groups.items()] if item.variant_groups else "—"

    # price_str removed, raw price passed below

    from app.domains.interaction.service.scoring import get_item_engagement_score
    engagement_score = get_item_engagement_score(item.id)

    data = {
        "id": item.id,
        "name": item.name,
        "category": item.category.name if item.category else "—",
        "brand": item.brand.name if item.brand else "—",
        "source": item.source.name if item.source else "—",
        "added": item.created_at.isoformat() if item.created_at else None,
        "last synced": last_synced.isoformat() if last_synced else None,
        "variants count": len(item.variants),
        "store count": len(store_links_data),
        "programs": list(set([lnk["program_name"] for lnk in store_links_data if lnk.get("program_name") and lnk["program_name"] != "—"])),
        "price": item.min_price,
        "variant groups": variant_groups if variant_groups != "—" else [],
        
        "engagement score": engagement_score,
        "views": item.view_count or 0,
        "likes": item.like_count or 0,
        "dislikes": item.dislike_count or 0,
        "comments": item.comment_count or 0,
        "shares": item.share_count or 0,
        "saves": item.save_count or 0,
        "click count": item.click_count or 0,
        
        "linked contents": len(item.linked_contents),
        "description": item.description or "—",
        "rating": item.rating,
        "review count": item.review_count or 0,
        "images count": len(item.images),
        "specs count": len(item.specifications),
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
                "value": {"label": user_name, "detail": preview},
                "is_labeled": True
            })

    # Actions are hardcoded in the template.

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
        "inspect_id": item.id,
        "item_name": item.name
    }

