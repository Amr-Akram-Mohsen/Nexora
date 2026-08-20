"""
Admin product management endpoints.
"""
from flask import Blueprint, jsonify, request, render_template
from app.web.routes.admin.helpers import (
    apply_admin_guard,
    parse_pagination_params,
    parse_sort_params,
    render_admin_rows_response,
)
from app.domains.product.models import Product
from app.domains.analytics import get_catalog_health_report
from app.domains.product.service.admin.admin import (
    get_admin_item_meta,
    get_admin_item_health_stats,
)
from app.application.product.admin import (
    delete_item_workflow,
    get_item_rows_workflow,
    get_item_detail_workflow,
    get_item_inspect_workflow,
)
from app.web.routes.admin.builders.item_builder import build_item_inspect_view_model

bp = Blueprint("api_item", __name__, url_prefix="/admin/products")
apply_admin_guard(bp)

_ITEM_SORT_MAP = {
    "id": Product.id,
    "created_at": Product.created_at,
    "name": Product.name,
    "click_count": Product.click_count,
    "view_count": Product.view_count,
}


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
        total=stats.get("total_items", 0),
    )
    stats["top_engagement_items_html"] = render_template(
        "admin/products/partials/_top_engagement.html",
        data=stats.get("top_engagement_items", []),
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
    page, per_page = parse_pagination_params(default_per_page=20)
    sort_col, sort_dir = parse_sort_params(_ITEM_SORT_MAP, Product.id)
    serialized, pagination = get_item_rows_workflow(request.args, page, per_page, sort_col, sort_dir)

    return jsonify({
        "products": serialized,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/<int:id>/detail", methods=["GET"])
def get_item_detail(id):
    """Return full variant and store-link details for a single product."""
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
    page, per_page = parse_pagination_params(default_per_page=20)
    sort_col, sort_dir = parse_sort_params(_ITEM_SORT_MAP, Product.id)
    serialized, pagination = get_item_rows_workflow(request.args, page, per_page, sort_col, sort_dir)

    return render_admin_rows_response(
        serialized,
        'product',
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


@bp.route("/<int:id>/inspect", methods=["GET"])
def inspect_item(id):
    aggregated_data = get_item_inspect_workflow(id)
    if not aggregated_data:
        return jsonify({"error": "Product not found"}), 404

    data = build_item_inspect_view_model(aggregated_data)
    data["domain"] = "products"
    return render_template("admin/components/_inspect.html", **data)
