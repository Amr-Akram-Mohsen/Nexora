from flask import Blueprint, jsonify, request, render_template
from app.web.routes.admin.helpers import apply_admin_guard, parse_pagination_params, render_admin_rows_response

bp = Blueprint("api_source", __name__, url_prefix="/admin/sources")
apply_admin_guard(bp)

@bp.route("/", methods=["GET"])
def list_sources():
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    from app.domains.taxonomy.service.admin.admin_providers_source import get_admin_sources_page
    pagination, serialized = get_admin_sources_page(page, per_page, search)
    return jsonify({
        "sources":  serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })

@bp.route("/health_stats", methods=["GET"])
def get_source_health_stats():
    from app.domains.taxonomy.service.admin.admin_providers_source import get_admin_source_health_stats
    return jsonify(get_admin_source_health_stats())

@bp.route("/rows", methods=["GET"])
def sources_rows():
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    from app.domains.taxonomy.service.admin.admin_providers_source import get_admin_sources_page
    pagination, serialized = get_admin_sources_page(page, per_page, search)
    return render_admin_rows_response(
        serialized, "source",
        total=pagination.total, pages=pagination.pages, page=pagination.page,
        domain_target_type="contents"
    )

@bp.route("/<int:id>/inspect", methods=["GET"])
def inspect_source(id):
    from app.domains.taxonomy.service.admin.admin import get_source_inspect_data
    from app.web.routes.admin.builders.taxonomy_builder import build_source_inspect_view_model
    
    aggregated_data = get_source_inspect_data(id)
    if not aggregated_data:
        return "Source not found.", 404
        
    data_dict = build_source_inspect_view_model(aggregated_data)
    return render_template("admin/components/_inspect.html", **data_dict)

@bp.route("/quality-data", methods=["GET"])
def get_sources_quality_data():
    from app.domains.taxonomy.service.admin.admin_providers_source import get_admin_sources_quality_data
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
