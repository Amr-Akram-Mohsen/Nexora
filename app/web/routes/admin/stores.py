from flask import Blueprint, jsonify, request, render_template
from app.web.routes.admin.helpers import apply_admin_guard, parse_pagination_params, render_admin_rows_response

bp = Blueprint("api_store", __name__, url_prefix="/admin/stores")
apply_admin_guard(bp)

@bp.route("/", methods=["GET"])
def list_stores():
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    network = request.args.get("network")
    country = request.args.get("country")
    sync_staleness = request.args.get("sync_staleness")
    
    from app.domains.product.service.admin_providers_store import get_admin_stores_page
    pagination, serialized = get_admin_stores_page(page, per_page, search, network, country, sync_staleness)
    return jsonify({
        "stores":   serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })

@bp.route("/health_stats", methods=["GET"])
def get_store_health_stats():
    from app.domains.product.service.admin_providers_store import get_admin_store_health_stats
    stats = get_admin_store_health_stats()
    stats["oos_by_store_html"] = render_template("admin/product_intelligence/partials/_oos_dist.html", data=stats.pop("oos_by_store"))
    stats["top_stale_stores_html"] = render_template("admin/product_intelligence/partials/_stale_list.html", data=stats.pop("top_stale_stores"))
    return jsonify(stats)

@bp.route("/coverage_stats", methods=["GET"])
def get_store_coverage_stats():
    from app.domains.product.service.admin_providers_store import get_admin_store_coverage_stats
    category_coverage, commission_rates = get_admin_store_coverage_stats()
    
    category_coverage_html = render_template("admin/product_intelligence/partials/_cat_coverage.html", data=category_coverage)
    commission_rates_html = render_template("admin/product_intelligence/partials/_comm_rates.html", data=commission_rates)

    return jsonify({
        "category_coverage_html": category_coverage_html,
        "commission_rates_html": commission_rates_html
    })

@bp.route("/affiliate_stats", methods=["GET"])
def get_store_affiliate_stats():
    from app.domains.product.service.admin_providers_store import get_admin_store_affiliate_stats
    stats = get_admin_store_affiliate_stats()
    stats["commission_rate_ranking_html"] = render_template("admin/product_intelligence/partials/_comm_ranking.html", data=stats.pop("commission_rate_ranking"))
    return jsonify(stats)

@bp.route("/pricing_stats", methods=["GET"])
def get_store_pricing_stats():
    from app.domains.product.service.admin_providers_store import get_admin_store_pricing_stats
    stats = get_admin_store_pricing_stats()
    stats["discount_depth_ranking_html"] = render_template("admin/product_intelligence/partials/_discount_ranking.html", data=stats.pop("discount_depth_ranking"))
    stats["pricing_alerts_html"] = render_template("admin/product_intelligence/partials/_pricing_alerts.html", oos_items_count=stats.pop("all_oos_items_count"), high_null_price_stores=stats.pop("high_null_price_stores"))
    return jsonify(stats)

@bp.route("/rows", methods=["GET"])
def stores_rows():
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    network = request.args.get("network")
    country = request.args.get("country")
    sync_staleness = request.args.get("sync_staleness")
    
    from app.domains.product.service.admin_providers_store import get_admin_stores_page
    pagination, serialized = get_admin_stores_page(page, per_page, search, network, country, sync_staleness)
    return render_admin_rows_response(
        serialized, "store",
        total=pagination.total, pages=pagination.pages, page=pagination.page,
        domain_target_type="products"
    )

@bp.route("/<int:id>/inspect", methods=["GET"])
def inspect_store(id):
    from app.domains.product.service.admin import get_admin_store_inspect_raw
    from app.domains.product.serializers import serialize_store_inspect_dto
    from app.web.routes.admin.builders.item_builder import build_store_inspect_view_model
    
    raw_result = get_admin_store_inspect_raw(id)
    if not raw_result:
        return "Store not found.", 404
        
    store, stats, product_count, currency_mix_list, avg_sync_age = raw_result
    dto = serialize_store_inspect_dto(store, stats, product_count, currency_mix_list, avg_sync_age)
    data_dict = build_store_inspect_view_model(dto)
    
    return render_template("admin/components/_inspect.html", **data_dict)
