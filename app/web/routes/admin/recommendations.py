"""
Admin content-product recommendation management endpoints.
"""
from flask import Blueprint, jsonify, request, render_template
from app.web.routes.admin.helpers import (
    apply_admin_guard,
    paginate_manual,
    render_admin_rows_response,
)
from app.domains.recommendation.service.admin.admin import (
    get_recommendation_stats,
    fetch_admin_matches_page,
    get_admin_context_performance,
    get_admin_entity_performance,
    get_admin_recommendation_health,
    get_admin_recommendation_trend,
    get_admin_slot_analysis,
    get_admin_match_inspect_data,
    get_admin_user_interests_data,
    delete_admin_match,
)
from app.web.routes.admin.builders.recommendation_builder import (
    build_match_inspect_view_model,
    build_user_interests_view_model,
)

bp = Blueprint("api_recommendation", __name__, url_prefix="/admin/recommendations")
apply_admin_guard(bp)


@bp.route("/stats", methods=["GET"])
def recommendation_stats():
    """Aggregate stats for content-product matches."""
    return jsonify(get_recommendation_stats())


@bp.route("/matches", methods=["GET"])
def list_matches():
    """Paginated list of content-product associations for admin inspection."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search = request.args.get("search", "").strip()
    entity_type = request.args.get("filter-entity-type", "").strip()
    ctr_range = request.args.get("filter-ctr-range", "").strip()

    total, pages, serialized = fetch_admin_matches_page(page, per_page, search, entity_type, ctr_range)
    return jsonify(paginate_manual(serialized, page, per_page, total))


@bp.route("/matches/rows", methods=["GET"])
def matches_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search = request.args.get("search", "").strip()
    entity_type = request.args.get("filter-entity-type", "").strip()
    ctr_range = request.args.get("filter-ctr-range", "").strip()

    total, pages, serialized = fetch_admin_matches_page(page, per_page, search, entity_type, ctr_range)

    display_items = []
    for r in serialized:
        display_items.append({
            "id": r["content_id"],
            "content_title": r['content_title'],
            "widget_impressions": r["widget_impressions"],
            "widget_ctr": r["widget_ctr"],
            "last_active": r["last_active"],
            "linked_items_count": r["linked_items_count"],
            "linked_items_list": [i['id'] for i in r["products"]],
        })

    return render_admin_rows_response(
        display_items,
        "rec",
        total=total,
        pages=pages,
        page=page,
    )


@bp.route("/matches/<int:content_id>/inspect", methods=["GET"])
def inspect_match(content_id):
    """Return server-rendered HTML for the recommendation inspect modal body."""
    aggregated_data = get_admin_match_inspect_data(content_id)
    if not aggregated_data:
        return "Content not found.", 404

    data = build_match_inspect_view_model(aggregated_data)
    return render_template("admin/components/_inspect.html", **data)


@bp.route("/context-performance", methods=["GET"])
def context_performance():
    return jsonify({"data": get_admin_context_performance()})


@bp.route("/entity-performance", methods=["GET"])
def entity_performance():
    return jsonify({"data": get_admin_entity_performance()})


@bp.route("/health", methods=["GET"])
def system_health():
    return jsonify(get_admin_recommendation_health())


@bp.route("/trend", methods=["GET"])
def recommendation_trend():
    return jsonify(get_admin_recommendation_trend())


@bp.route("/slot-analysis", methods=["GET"])
def slot_analysis():
    return jsonify(get_admin_slot_analysis())


@bp.route("/user_interests/<int:user_id>/inspect", methods=["GET"])
def inspect_user_interests(user_id):
    aggregated_data = get_admin_user_interests_data(user_id)
    if not aggregated_data:
        return "User not found.", 404

    data = build_user_interests_view_model(aggregated_data)
    return render_template("admin/components/_inspect.html", **data)


@bp.route("/matches/<int:content_id>/<int:product_id>", methods=["DELETE"])
def unlink_match(content_id, product_id):
    """Remove a content-product association."""
    delete_admin_match(content_id, product_id)
    return jsonify({"success": True, "message": "Association removed."})
