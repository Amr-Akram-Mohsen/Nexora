# app/admin/providers.py
"""
Admin provider management endpoints (sources and stores).

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- N+1 loops replaced with aggregate subqueries for content/item counts and
  latest activity per provider (R-04).
- All queries use modern select() style (R-07).
- Shared pagination helpers from app.web.routes.admin.helpers (R-18, R-21).
- Extracted _fetch_sources_page() and _fetch_stores_page() helpers to
  eliminate duplication between JSON listing and HTML partial endpoints.
"""
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.taxonomy.models import Source
from app.domains.content.models import Content
from app.domains.item.models import Store, Item, ItemVariant, ItemStoreLink
from app.domains.external.models import LastAPIFetch
from app.domains.interaction.models import View, ItemClick
from app.web.routes.admin.helpers import parse_pagination_params, make_rows_response
from sqlalchemy import select, func, or_, case

bp = Blueprint("api_provider", __name__, url_prefix="/admin/providers")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all provider endpoints require admin privilege."""
    pass


# ─────────────────────────────────────────────
# SOURCES (content providers)
# ─────────────────────────────────────────────

@bp.route("/sources", methods=["GET"])
def list_sources():
    """Paginated listing of sources/content providers with counts and latest content."""
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    from app.domains.taxonomy.service.admin_providers_source import get_admin_sources_page
    pagination, serialized = get_admin_sources_page(page, per_page, search)
    return jsonify({
        "sources":  serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/sources/health_stats", methods=["GET"])
def get_source_health_stats():
    """Return fast KPI stats for the sources health dashboard."""
    from app.domains.taxonomy.service.admin_providers_source import get_admin_source_health_stats
    return jsonify(get_admin_source_health_stats())


# ─────────────────────────────────────────────
# STORES (product / affiliate providers)
# ─────────────────────────────────────────────

@bp.route("/stores", methods=["GET"])
def list_stores():
    """Paginated listing of stores/commercial providers with counts and latest products."""
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    network = request.args.get("network")
    country = request.args.get("country")
    sync_staleness = request.args.get("sync_staleness")
    
    from app.domains.item.service.admin_providers_store import get_admin_stores_page
    pagination, serialized = get_admin_stores_page(page, per_page, search, network, country, sync_staleness)
    return jsonify({
        "stores":   serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/stores/health_stats", methods=["GET"])
def get_store_health_stats():
    """Return fast KPI stats for the stores/sync health dashboard."""
    from app.domains.item.service.admin_providers_store import get_admin_store_health_stats
    stats = get_admin_store_health_stats()
    stats["oos_by_store_html"] = render_template("admin/product_intelligence/partials/_oos_dist.html", data=stats.pop("oos_by_store"))
    stats["top_stale_stores_html"] = render_template("admin/product_intelligence/partials/_stale_list.html", data=stats.pop("top_stale_stores"))
    return jsonify(stats)


@bp.route("/stores/coverage_stats", methods=["GET"])
def get_store_coverage_stats():
    """Return affiliate coverage and commission stats."""
    from app.domains.item.service.admin_providers_store import get_admin_store_coverage_stats
    category_coverage, commission_rates = get_admin_store_coverage_stats()
    
    category_coverage_html = render_template("admin/product_intelligence/partials/_cat_coverage.html", data=category_coverage)
    commission_rates_html = render_template("admin/product_intelligence/partials/_comm_rates.html", data=commission_rates)

    return jsonify({
        "category_coverage_html": category_coverage_html,
        "commission_rates_html": commission_rates_html
    })

@bp.route("/stores/affiliate_stats", methods=["GET"])
def get_store_affiliate_stats():
    """Return in-depth affiliate, commission, and tracking health stats."""
    from app.domains.item.service.admin_providers_store import get_admin_store_affiliate_stats
    stats = get_admin_store_affiliate_stats()
    stats["commission_rate_ranking_html"] = render_template("admin/product_intelligence/partials/_comm_ranking.html", data=stats.pop("commission_rate_ranking"))

    return jsonify(stats)

@bp.route("/stores/pricing_stats", methods=["GET"])
def get_store_pricing_stats():
    """Return pricing intelligence stats: discounts, staleness, currency mix."""
    from app.domains.item.service.admin_providers_store import get_admin_store_pricing_stats
    stats = get_admin_store_pricing_stats()
    stats["discount_depth_ranking_html"] = render_template("admin/product_intelligence/partials/_discount_ranking.html", data=stats.pop("discount_depth_ranking"))
    stats["pricing_alerts_html"] = render_template("admin/product_intelligence/partials/_pricing_alerts.html", oos_items_count=stats.pop("all_oos_items_count"), high_null_price_stores=stats.pop("high_null_price_stores"))

    return jsonify(stats)

@bp.route("/sources/rows", methods=["GET"])
def sources_rows():
    """Return server-rendered HTML rows partial for sources AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    from app.domains.taxonomy.service.admin_providers_source import get_admin_sources_page
    pagination, serialized = get_admin_sources_page(page, per_page, search)
    html = render_template("admin/components/_rows.html", items=serialized, domain_type="source", domain_target_type="contents")
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


@bp.route("/stores/rows", methods=["GET"])
def stores_rows():
    """Return server-rendered HTML rows partial for stores AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    network = request.args.get("network")
    country = request.args.get("country")
    sync_staleness = request.args.get("sync_staleness")
    
    from app.domains.item.service.admin_providers_store import get_admin_stores_page
    pagination, serialized = get_admin_stores_page(page, per_page, search, network, country, sync_staleness)
    html = render_template("admin/components/_rows.html", items=serialized, domain_type="store", domain_target_type="items")
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


# ─────────────────────────────────────────────
# INSPECT ENDPOINTS
# ─────────────────────────────────────────────

@bp.route("/sources/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_source(id):
    from app.web.routes.admin.tables import get_inspect_table
    from app.domains.taxonomy.service.admin_providers_source import build_admin_source_inspect_data
    data_dict = build_admin_source_inspect_data(id)
    if not data_dict:
        return "Source not found.", 404
        
    data_dict["inspect_table"] = get_inspect_table("sources", data_dict.pop("raw_data"))
    return render_template("admin/components/_inspect.html", **data_dict)

@bp.route("/stores/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_store(id):
    from app.web.routes.admin.tables import get_inspect_table
    from app.domains.item.service.admin_providers_store import build_admin_store_inspect_data
    data_dict = build_admin_store_inspect_data(id)
    if not data_dict:
        return "Store not found.", 404
        
    data_dict["inspect_table"] = get_inspect_table("stores", data_dict.pop("raw_data"))
    return render_template("admin/components/_inspect.html", **data_dict)


@bp.route("/sources/quality-data", methods=["GET"])
def get_sources_quality_data():
    from app.domains.taxonomy.service.admin_providers_source import get_admin_sources_quality_data
    quality_leaderboard, scrape_leaderboard, freshness_index, word_count_data, yield_data = get_admin_sources_quality_data()
    
    quality_leaderboard_html = render_template("admin/providers/partials/_quality_leaderboard.html", data=quality_leaderboard[:15])
    scrape_leaderboard_html = render_template("admin/providers/partials/_scrape_leaderboard.html", data=scrape_leaderboard[:15])
    freshness_index_html = render_template("admin/providers/partials/_freshness_index.html", data=freshness_index[:15])

    return jsonify({
        "quality_leaderboard_html": quality_leaderboard_html,
        "scrape_leaderboard_html": scrape_leaderboard_html,
        "freshness_index_html": freshness_index_html,
        "word_counts": word_count_data,
        "yield_rate": yield_data
    })
