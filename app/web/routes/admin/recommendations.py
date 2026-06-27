# app/admin/recommendations.py
"""
Admin content-item recommendation management endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- @admin_required added explicitly to unlink_match as a belt-and-suspenders
  guard for the DELETE operation (R-19).
"""
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.item.models import Item
from app.domains.relationships import content_items
from app.web.routes.admin.helpers import paginate_manual, make_rows_response
from app.domains.recommendation.service.admin import (
    get_recommendation_stats,
    fetch_admin_matches_page,
    build_admin_match_inspect_data,
    get_admin_context_performance,
    get_admin_entity_performance,
    get_admin_recommendation_health,
    get_admin_recommendation_trend,
    get_admin_slot_analysis,
    build_admin_user_interests_data
)
from app.application.recommendation.admin import unlink_match_workflow

bp = Blueprint("api_recommendation", __name__, url_prefix="/admin/recommendations")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all recommendation management endpoints require admin privilege."""
    pass


@bp.route("/stats", methods=["GET"])
def recommendation_stats():
    """Aggregate stats for content-item matches."""
    return jsonify(get_recommendation_stats())


@bp.route("/matches", methods=["GET"])
def list_matches():
    """Paginated list of content-item associations for admin inspection."""
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search   = request.args.get("search", "").strip()
    entity_type = request.args.get("filter-entity-type", "").strip()
    ctr_range = request.args.get("filter-ctr-range", "").strip()
    
    total, pages, serialized = fetch_admin_matches_page(page, per_page, search, entity_type, ctr_range)
    return jsonify(paginate_manual(serialized, page, per_page, total))


@bp.route("/matches/rows", methods=["GET"])
def matches_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search   = request.args.get("search", "").strip()
    entity_type = request.args.get("filter-entity-type", "").strip()
    ctr_range = request.args.get("filter-ctr-range", "").strip()
    
    total, pages, serialized = fetch_admin_matches_page(page, per_page, search, entity_type, ctr_range)
    
    display_items = []
    for r in serialized:
        item_ids_str = ", ".join(f"{i['id']}" for i in r['items'])
        display_items.append({
            "id": r["content_id"],
            "content-title": f"{r['content_title']} (#{r['content_id']})",
            "widget-impressions": "{:,}".format(r["widget_impressions"]),
            "widget-ctr": r["widget_ctr"],
            "last-active": r["last_active"],
            "linked-items-count": r["linked_items_count"],
            "linked-items-list": [i['id'] for i in r["items"]]
        })

    html = render_template("admin/components/_rows.html", items=display_items, domain_type="rec")
    return make_rows_response(html, total=total, pages=pages, page=page)


@bp.route("/matches/<int:content_id>/inspect", methods=["GET"])
def inspect_match(content_id):
    """Return server-rendered HTML for the recommendation inspect modal body."""
    data = build_admin_match_inspect_data(content_id)
    if not data:
        return "Content not found.", 404

    from app.web.routes.admin.tables import get_inspect_table
    inspect_table = get_inspect_table("recommendations", data["raw_data"])
    
    return render_template(
        "admin/components/_inspect.html",
        inspect_table=inspect_table,
        linked_items=data["linked_items"],
        inspect_id=data["inspect_id"]
    )

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
    data = build_admin_user_interests_data(user_id)
    if not data:
        return "User not found.", 404
        
    from app.web.routes.admin.tables import get_inspect_table
    inspect_table = get_inspect_table("user_interests", data["raw_data"])
    
    return render_template(
        "admin/components/_inspect.html",
        inspect_table=inspect_table,
        actions=[]
    )


@bp.route("/matches/<int:content_id>/<int:item_id>", methods=["DELETE"])
def unlink_match(content_id, item_id):
    """Remove a content-item association."""
    unlink_match_workflow(content_id, item_id)
    return jsonify({"success": True, "message": "Association removed."})
