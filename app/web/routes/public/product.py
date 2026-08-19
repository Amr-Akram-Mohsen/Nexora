import logging
from flask import Blueprint, request, render_template, jsonify, redirect, url_for, abort
from flask_login import current_user
from app.application.product.public import (
    get_catalog_data,
    get_item_page_data,
    get_item_spec_groups_workflow,
    get_comparison_data
)
from app.shared.request import get_client_ip
from app.domains.interaction.service import record_view
from app.shared.constants.core import TargetType
from app.shared.utils.logging import log_route_start, log_route_success, log_route_error

logger = logging.getLogger(__name__)

from app.web.routes.constants import PUBLIC_TEMPLATES

bp = Blueprint("product", __name__, template_folder=PUBLIC_TEMPLATES)


@bp.route("/product/<int:product_id>/view_full_specs", methods=["POST"])
def view_full_specs(product_id):
    full_details = get_item_spec_groups_workflow(product_id)
    if full_details is None:
        abort(404)

    html = render_template(
        "commercial/features/full-details.html",
        product={"structured_details": {"groups": full_details}},
        full_details=full_details,
    )
    return jsonify({"html": html})


@bp.route("/deals")
def deals():
    from app.web.helpers.filters import parse_active_filters
    
    active_filters = parse_active_filters(
        list_names=["category", "brand", "store", "type"],
        scalar_names=["min_price", "max_price"]
    )
    page = request.args.get("page", 1, type=int)

    log_route_start(logger, "/deals", page=page)

    data = get_catalog_data(active_filters, page=page)

    item_count = len(data.get("products") or [])
    log_route_success(logger, "/deals", products=item_count, template="catalog-page.html")

    return render_template(
        "commercial/catalog/catalog-page.html",
        target_type="commercial",
        allowed_filters=["category", "brand", "store"],
        active_filters=active_filters,
        **data,
    )


@bp.route("/products/<int:product_id>")
def item_page(product_id):
    from app.application.product.get_product_page import record_item_view
    from app.core.extensions import db

    log_route_start(logger, f"/products/{product_id}")

    user = current_user if current_user.is_authenticated else None
    ip_address = None if user else get_client_ip()

    data = get_item_page_data(product_id)
    if not data:
        logger.warning("[ROUTE][/products/%d] no data returned — 404", product_id)
        abort(404)

    record_item_view(product_id, user, ip_address)

    log_route_success(logger, f"/products/{product_id}", template="product.html")

    return render_template("commercial/dispatcher/page.html", **data)


@bp.route("/compare")
def compare():
    """Side-by-side comparison of 2-4 products."""
    ids_str = request.args.get("ids", "")
    try:
        product_ids = [
            int(id_strip) for id_strip in ids_str.split(",") if id_strip.strip()
        ]
    except ValueError:
        product_ids = []

    if not product_ids:
        return redirect(url_for("product.deals"))

    data = get_comparison_data(product_ids)
    if not data:
        return redirect(url_for("product.deals"))

    return render_template(
        "commercial/catalog/compare-page.html", target_type="commercial", **data
    )
