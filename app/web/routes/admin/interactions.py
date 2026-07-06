# app/admin/interactions.py
"""
Admin interaction management endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- Interaction stats endpoint reads from the 60-second cached
  get_interactions_breakdown() instead of issuing 8 independent queries (R-03).
- All queries use modern select() style (R-07).
- Shared pagination helpers from app.web.routes.admin.helpers (R-18, R-21).
"""
from flask import Blueprint, jsonify, request, render_template
from app.web.routes.admin.helpers import apply_admin_guard
from app.core.extensions import db
from app.domains.interaction.models import Comment, Reaction, View, Save, Share, ItemClick
from app.domains.interaction.service.query import (
    get_interactions_breakdown,
    get_reaction_stats,
    get_view_stats,
    get_save_stats,
    get_share_stats,
    get_click_stats,
)
from app.domains.interaction.service.admin import (
    get_admin_comments_page,
    delete_admin_comment,
    flag_admin_comment_as_spam,
    get_admin_reactions_page,
    get_admin_views_page,
    get_admin_clicks_page,
    get_admin_saves_page,
    get_admin_shares_page
)
from app.domains.user.models import User
from app.web.routes.admin.helpers import parse_pagination_params, render_admin_rows_response
from sqlalchemy import select, func, or_
from datetime import datetime
from app.domains.interaction.service.admin import (
    map_comment_for_rows, map_reaction_for_rows, map_view_for_rows,
    map_click_for_rows, map_save_for_rows, map_share_for_rows
)

bp = Blueprint("api_interaction", __name__, url_prefix="/admin/interactions")


apply_admin_guard(bp)


# ─────────────────────────────────────────────
# COMMENTS
# ─────────────────────────────────────────────

@bp.route("/comments", methods=["GET"])
def list_comments():
    """Paginated, enriched comment listing with user and target info."""
    page, per_page = parse_pagination_params(default_per_page=25)
    sentiment   = request.args.get("sentiment", "").strip()
    target_type = request.args.get("target_type", "").strip()
    search      = request.args.get("search", "").strip()
    user_search = request.args.get("comments_user", request.args.get("user", "")).strip()
    start_date  = request.args.get("comments_start_date", request.args.get("start_date", "")).strip()
    end_date    = request.args.get("comments_end_date", request.args.get("end_date", "")).strip()

    pagination, serialized = get_admin_comments_page(
        page, per_page, sentiment, target_type, search, user_search, start_date, end_date
    )

    return jsonify({
        "items":    serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/comments/<int:id>", methods=["DELETE"])
def delete_comment(id):
    """Delete a comment and all its replies."""
    if delete_admin_comment(id):
        return jsonify({"success": True, "message": "Comment deleted."})
    return jsonify({"error": "Comment not found"}), 404

@bp.route("/comments/<int:id>/flag", methods=["POST"])
def flag_comment(id):
    """Flag a comment as spam by marking its sentiment."""
    if flag_admin_comment_as_spam(id):
        return jsonify({"success": True, "message": "Comment flagged as spam."})
    return jsonify({"error": "Comment not found"}), 404


# ─────────────────────────────────────────────
# REACTIONS
# ─────────────────────────────────────────────

@bp.route("/reactions", methods=["GET"])
def list_reactions():
    """Paginated reactions list for moderation view."""
    page, per_page = parse_pagination_params(default_per_page=25)
    reaction_type = request.args.get("type", "").strip()
    target = request.args.get("search", "").strip()
    user_search = request.args.get("reactions_user", request.args.get("user", "")).strip()

    pagination, serialized = get_admin_reactions_page(
        page, per_page, reaction_type, target, user_search
    )

    return jsonify({
        "items":    serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/views", methods=["GET"])
def list_views():
    """Paginated list of views aggregated by target."""
    page, per_page = parse_pagination_params(default_per_page=25)
    target = request.args.get("search", "").strip()
    start_date = request.args.get("views_start_date", request.args.get("start_date", "")).strip()
    end_date = request.args.get("views_end_date", request.args.get("end_date", "")).strip()

    return jsonify(get_admin_views_page(page, per_page, target, start_date, end_date))


@bp.route("/clicks", methods=["GET"])
def list_clicks():
    """Paginated click logs aggregated by external link."""
    page, per_page = parse_pagination_params(default_per_page=25)
    target = request.args.get("search", "").strip()
    destination = request.args.get("clicks_destination", request.args.get("destination", "")).strip()

    return jsonify(get_admin_clicks_page(page, per_page, target, destination))



@bp.route("/saves", methods=["GET"])
def list_saves():
    """Paginated list of saves with user and target details."""
    page, per_page = parse_pagination_params(default_per_page=25)
    target = request.args.get("search", "").strip()
    user_search = request.args.get("saves_user", request.args.get("user", "")).strip()

    pagination, serialized = get_admin_saves_page(
        page, per_page, target, user_search
    )

    return jsonify({
        "items":    serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/shares", methods=["GET"])
def list_shares():
    """Paginated list of shares with user and target details."""
    page, per_page = parse_pagination_params(default_per_page=25)
    target = request.args.get("search", "").strip()
    user_search = request.args.get("shares_user", request.args.get("user", "")).strip()

    pagination, serialized = get_admin_shares_page(
        page, per_page, target, user_search
    )

    return jsonify({
        "items":    serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })


# ─────────────────────────────────────────────
# HTML PARTIAL ROWS + INSPECT ENDPOINTS
# ─────────────────────────────────────────────







@bp.route("/comments/rows", methods=["GET"])
def comments_rows():
    """Return server-rendered HTML rows partial for comments AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    sentiment   = request.args.get("sentiment", "").strip()
    target_type = request.args.get("target_type", "").strip()
    search      = request.args.get("search", "").strip()
    user_search = request.args.get("comments_user", request.args.get("user", "")).strip()
    start_date  = request.args.get("comments_start_date", request.args.get("start_date", "")).strip()
    end_date    = request.args.get("comments_end_date", request.args.get("end_date", "")).strip()

    pagination, serialized = get_admin_comments_page(
        page, per_page, sentiment, target_type, search, user_search, start_date, end_date
    )

    display_items = [map_comment_for_rows(c) for c in serialized]
    return render_admin_rows_response(
        display_items, "comment",
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page
    )



@bp.route("/comments/<int:id>/inspect", methods=["GET"])
def inspect_comment(id):
    """Return server-rendered HTML for the comment inspect modal body."""
    from app.application.interaction.admin import get_comment_inspect_workflow
    from app.web.routes.admin.builders.interaction_builder import build_comment_inspect_view_model
    
    aggregated_data = get_comment_inspect_workflow(id)
    if not aggregated_data:
        return "Comment not found.", 404
        
    data = build_comment_inspect_view_model(aggregated_data)
    return render_template(
        "admin/components/_inspect.html",
        **data
    )
@bp.route("/clicks/<int:link_id>/inspect", methods=["GET"])
def inspect_clicks(link_id):
    """Return server-rendered HTML for recent clicks on a given store link."""
    from app.application.interaction.admin import get_link_clicks_workflow
    from app.web.routes.admin.builders.interaction_builder import build_link_clicks_view_model
    
    aggregated_data = get_link_clicks_workflow(link_id)
    if not aggregated_data:
         return "Link data not found.", 404

    data = build_link_clicks_view_model(aggregated_data)
    return render_template(
        "admin/components/_inspect.html",
        **data
    )


@bp.route("/reactions/rows", methods=["GET"])
def reactions_rows():
    """Return server-rendered HTML rows partial for reactions AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    reaction_type = request.args.get("reactions_type", "").strip()
    search        = request.args.get("search", "").strip()
    user_search = request.args.get("reactions_user", request.args.get("user", "")).strip()

    pagination, serialized = get_admin_reactions_page(
        page, per_page, reaction_type, search, user_search
    )

    display_items = [map_reaction_for_rows(r) for r in serialized]
    return render_admin_rows_response(
        display_items, "reaction",
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
        hide_action_column=True
    )


@bp.route("/views/rows", methods=["GET"])
def views_rows():
    """Return server-rendered HTML rows partial for views AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    start_date = request.args.get("views_start_date", "").strip()
    end_date   = request.args.get("views_end_date", "").strip()
    search     = request.args.get("search", "").strip()

    data = get_admin_views_page(page, per_page, search, start_date, end_date)

    serialized = [map_view_for_rows(v) for v in data["items"]]
    return render_admin_rows_response(
        serialized, "view",
        total=data["total"], pages=data["pages"], page=data["page"],
        hide_action_column=True
    )


@bp.route("/clicks/rows", methods=["GET"])
def clicks_rows():
    """Return server-rendered HTML rows partial for clicks AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    destination = request.args.get("clicks_destination", request.args.get("destination", "")).strip()

    data = get_admin_clicks_page(page, per_page, search, destination)

    serialized = [map_click_for_rows(r) for r in data["items"]]
    return render_admin_rows_response(
        serialized, "click",
        total=data["total"], pages=data["pages"], page=data["page"],
        hide_action_column=False
    )


@bp.route("/saves/rows", methods=["GET"])
def saves_rows():
    """Return server-rendered HTML rows partial for saves AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    user_search = request.args.get("saves_user", request.args.get("user", "")).strip()

    pagination, serialized = get_admin_saves_page(
        page, per_page, search, user_search
    )

    display_items = [map_save_for_rows(s) for s in serialized]
    return render_admin_rows_response(
        display_items, "save",
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
        hide_action_column=True
    )

@bp.route("/shares/rows", methods=["GET"])
def shares_rows():
    """Return server-rendered HTML rows partial for shares AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    user_search = request.args.get("shares_user", request.args.get("user", "")).strip()

    pagination, serialized = get_admin_shares_page(
        page, per_page, search, user_search
    )

    display_items = [map_share_for_rows(s) for s in serialized]
    return render_admin_rows_response(
        display_items, "share",
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
        hide_action_column=True
    )


# ─────────────────────────────────────────────
# STATS (read from 60s cache — R-03)
# ─────────────────────────────────────────────

@bp.route("/stats", methods=["GET"])
def interactions_stats():
    """Unified stats endpoint — returns breakdown + total + reaction split."""
    breakdown = get_interactions_breakdown()
    total = sum(v for k, v in breakdown.items() if not k.startswith("_"))

    return jsonify({
        "comments":   breakdown.get("comments", 0),
        "reactions":  breakdown.get("reactions", 0),
        "views":      breakdown.get("views", 0),
        "saves":      breakdown.get("saves", 0),
        "shares":     breakdown.get("shares", 0),
        "item_clicks": breakdown.get("clicks", 0),
        "likes":      breakdown.get("_likes", 0),
        "dislikes":   breakdown.get("_dislikes", 0),
        "total":      total,
    })


@bp.route("/reactions/stats", methods=["GET"])
def reactions_stats():
    return jsonify(get_reaction_stats())


@bp.route("/views/stats", methods=["GET"])
def views_stats():
    return jsonify(get_view_stats())


@bp.route("/saves/stats", methods=["GET"])
def saves_stats():
    return jsonify(get_save_stats())


@bp.route("/shares/stats", methods=["GET"])
def shares_stats():
    return jsonify(get_share_stats())


@bp.route("/clicks/stats", methods=["GET"])
def clicks_stats():
    return jsonify(get_click_stats())


@bp.route("/analytics", methods=["GET"])
def analytics_dashboard():
    from app.domains.interaction.service.analytics import get_analytics_dashboard_data
    return jsonify(get_analytics_dashboard_data())
