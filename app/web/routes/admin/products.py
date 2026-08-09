# app/admin/products.py
"""
Admin product management endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- store_links removed from listing serialization; new /admin/products/<id>/detail
  endpoint serves the inspect modal (R-14).
- min_price and store_count computed via SQL subqueries instead of ORM
  relationship traversal during serialization (R-15).
- Shared helpers from app.web.routes.admin.helpers for pagination and sort parsing (R-18, R-21).
"""
from flask import Blueprint, jsonify, request, render_template
from app.web.routes.admin.helpers import apply_admin_guard
from app.core.extensions import db
from app.domains.product.models import Product, ProductVariant, ProductStoreLink, Store, ProductImage
from app.domains.taxonomy.models import Category, Brand, Source
from app.web.routes.admin.helpers import parse_pagination_params, parse_sort_params, render_admin_rows_response
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload
from app.domains.product.models import ProductSpecification
from app.domains.interaction.models import Comment
from app.domains.analytics import get_catalog_health_report
from app.domains.product.service.admin.admin import (
    get_admin_item_meta,
    get_admin_item_health_stats,
    load_admin_item_aggregates,
    build_admin_items_query,
    get_admin_item_inspect_raw,
    get_admin_items_page,
    get_admin_item
)
from app.application.product.admin import delete_item_workflow

bp = Blueprint("api_item", __name__, url_prefix="/admin/products")




apply_admin_guard(bp)


# ─────────────────────────────────────────────
# SORT MAP
# ─────────────────────────────────────────────

_ITEM_SORT_MAP = {
    "id":          Product.id,
    "created_at":  Product.created_at,
    "name":        Product.name,
    "click_count": Product.click_count,
    "view_count":  Product.view_count,
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
    """Return fast KPI stats for the product catalog health dashboard."""
    stats = get_admin_item_health_stats()
    
    stats["product_type_distribution_html"] = render_template(
        "admin/products/partials/_type_distribution.html",
        data=stats.get("product_type_distribution", []),
        total=stats.get("total_items", 0)
    )
    
    stats["top_engagement_items_html"] = render_template(
        "admin/products/partials/_top_engagement.html",
        data=stats.get("top_engagement_items", [])
    )
    
    return jsonify(stats)

@bp.route("/catalog-health", methods=["GET"])
def catalog_health():
    """Renders the full Catalog Health Dashboard."""
    data = get_catalog_health_report()
    return render_template("admin/products/catalog_health.html", data=data)

@bp.route("/", methods=["GET"])
def list_items():
    """Paginated, filterable product listing for the admin control panel."""
    from app.application.product.admin import get_item_rows_workflow
    page, per_page = parse_pagination_params(default_per_page=20)
    sort_col, sort_dir = parse_sort_params(_ITEM_SORT_MAP, Product.id)

    serialized, pagination = get_item_rows_workflow(request.args, page, per_page, sort_col, sort_dir)

    return jsonify({
        "products":    serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/<int:id>/detail", methods=["GET"])
def get_item_detail(id):
    """
    Return full variant and store-link details for a single product.
    Used by the admin inspect modal (replaces embedding store_links in
    every listing row).
    """
    from app.application.product.admin import get_item_detail_workflow
    
    data = get_item_detail_workflow(id)
    if not data:
        return jsonify({"error": "Product not found"}), 404

    return jsonify(data)


@bp.route("/<int:id>", methods=["DELETE"])
def delete_item(id):
    """Delete an product and all its variants, store links, and images."""
    deleted_name = delete_item_workflow(id)
    if not deleted_name:
        return jsonify({"error": "Product not found"}), 404

    return jsonify({"success": True, "message": f"Product '{deleted_name}' deleted successfully."})


@bp.route("/rows", methods=["GET"])
def items_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    from app.application.product.admin import get_item_rows_workflow
    page, per_page = parse_pagination_params(default_per_page=20)
    sort_col, sort_dir = parse_sort_params(_ITEM_SORT_MAP, Product.id)

    serialized, pagination = get_item_rows_workflow(request.args, page, per_page, sort_col, sort_dir)

    return render_admin_rows_response(
        serialized, 'product',
        total=pagination.total, pages=pagination.pages, page=pagination.page
    )


@bp.route("/<int:id>/inspect", methods=["GET"])
def inspect_item(id):
    from app.application.product.admin import get_item_inspect_workflow
    from app.web.routes.admin.builders.item_builder import build_item_inspect_view_model
    
    aggregated_data = get_item_inspect_workflow(id)
    if not aggregated_data:
        return jsonify({"error": "Product not found"}), 404
        
    data = build_item_inspect_view_model(aggregated_data)
    data["domain"] = "products"
    return render_template("admin/components/_inspect.html", **data)


