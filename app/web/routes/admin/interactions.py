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
from app.core.decorators import admin_required
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
    build_admin_comment_inspect_data,
    get_admin_reactions_page,
    get_admin_views_page,
    get_admin_clicks_page,
    get_admin_saves_page,
    get_admin_shares_page
)
from app.domains.user.models import User
from app.web.routes.admin.helpers import parse_pagination_params, make_rows_response
from sqlalchemy import select, func, or_
from datetime import datetime

bp = Blueprint("api_interaction", __name__, url_prefix="/admin/interactions")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all interaction management endpoints require admin privilege."""
    pass


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

def _serialize_comment(c, users, content_titles, item_names):
    """Shared comment serializer for both JSON and HTML endpoints."""
    user = users.get(c.user_id)
    target_title = (
        content_titles.get(c.target_id)
        if c.target_type == "content"
        else item_names.get(c.target_id)
    )
    return {
        "id":           c.id,
        "content":      c.content,
        "preview":      c.content[:120] + ("…" if len(c.content) > 120 else ""),
        "user_id":      c.user_id,
        "user_name":    user["name"] if user else f"User #{c.user_id}",
        "user_email":   user["email"] if user else None,
        "parent_id":    c.parent_id,
        "sentiment":    c.sentiment or "neutral",
        "target_type":  c.target_type,
        "target_id":    c.target_id,
        "like_count":   c.like_count,
        "dislike_count": c.dislike_count,
        "replies_count": c.replies_count,
        "replies":      c.replies,
        "target_title": target_title or f"{c.target_type.capitalize()} #{c.target_id}",
        "created_at":   c.created_at.isoformat() if c.created_at else None,
    }


def _load_interaction_context(items):
    """Batch-load user info and target titles for a list of interaction items."""
    from app.domains.content.models import Content
    from app.domains.item.models import Item
    user_ids     = {c.user_id for c in items}
    content_ids  = {c.target_id for c in items if c.target_type == "content"}
    item_ids     = {c.target_id for c in items if c.target_type == "item"}
    users, content_titles, item_names = {}, {}, {}
    if user_ids:
        rows = db.session.execute(select(User.id, User.name, User.email).where(User.id.in_(user_ids))).mappings().all()
        users = {r["id"]: r for r in rows}
    if content_ids:
        rows = db.session.execute(select(Content.id, Content.title).where(Content.id.in_(content_ids))).mappings().all()
        content_titles = {r["id"]: r["title"] for r in rows}
    if item_ids:
        rows = db.session.execute(select(Item.id, Item.name).where(Item.id.in_(item_ids))).mappings().all()
        item_names = {r["id"]: r["name"] for r in rows}
    return users, content_titles, item_names


def _load_target_titles(items, type_attr="target_type", id_attr="target_id"):
    """
    Batch-load content titles and item names for a list of objects that have
    a target_type / target_id pair.

    Args:
        items:     Iterable of ORM instances or mappings.
        type_attr: Attribute name for the target type string (default "target_type").
        id_attr:   Attribute name for the target id (default "target_id").

    Returns:
        (content_titles, item_names) — both are {id: str} dicts.
    """
    from app.domains.content.models import Content
    from app.domains.item.models import Item
    content_ids = {getattr(obj, id_attr) for obj in items if getattr(obj, type_attr) == "content"}
    item_ids    = {getattr(obj, id_attr) for obj in items if getattr(obj, type_attr) == "item"}
    content_titles, item_names = {}, {}
    if content_ids:
        rows = db.session.execute(
            select(Content.id, Content.title).where(Content.id.in_(content_ids))
        ).mappings().all()
        content_titles = {r["id"]: r["title"] for r in rows}
    if item_ids:
        rows = db.session.execute(
            select(Item.id, Item.name).where(Item.id.in_(item_ids))
        ).mappings().all()
        item_names = {r["id"]: r["name"] for r in rows}
    return content_titles, item_names




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

    display_items = [
        {
            "id": c["id"],
            "title": c["target_title"],
            "target_type": c["target_type"],
            "preview": c["preview"],
            "sentiment": c["sentiment"],
            "likes": f"👍 {c['like_count']} 👎 {c['dislike_count']}",
            "replies": str(c["replies_count"]),
            "thread?": "Reply" if c["parent_id"] else "—",
            "date": c["created_at"][:10] if c["created_at"] else "—",
            "username": c["user_name"],
        } for c in serialized
    ]

    html = render_template("admin/components/_rows.html", items=display_items, domain_type="comment")
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


def build_comment_inspect_data(id):
    raw_data = build_admin_comment_inspect_data(id)
    if not raw_data:
        return None
        
    from app.web.routes.admin.tables import get_inspect_table
    inspect_table = get_inspect_table("comments", raw_data["raw_data"])
    
    return {
        "inspect_table": inspect_table,
        "actions": raw_data["actions"],
        "inspect_id": raw_data["inspect_id"]
    }


@bp.route("/comments/<int:id>/inspect", methods=["GET"])
def inspect_comment(id):
    """Return server-rendered HTML for the comment inspect modal body."""
    data = build_comment_inspect_data(id)
    if not data:
        return "Comment not found.", 404
    return render_template(
        "admin/components/_inspect.html",
        **data
    )

@bp.route("/clicks/<int:link_id>/inspect", methods=["GET"])
def inspect_clicks(link_id):
    """Return server-rendered HTML for recent clicks on a given store link."""
    from app.domains.interaction.service.inspect import get_link_clicks_metrics
    metrics = get_link_clicks_metrics(link_id)
    
    if not metrics:
         return "Link data not found.", 404

    from app.web.routes.admin.tables import get_inspect_table
    
    link_data = metrics["link_data"]
    total_clicks = metrics["total_clicks"]
    latest_click = metrics["latest_click"]
    country_stats = metrics["country_stats"]
    referrer_stats = metrics["referrer_stats"]
    
    top_countries = [{"label": c or 'Unknown', "count": cnt} for c, cnt in country_stats] if country_stats else "—"
    top_referrers = [{"label": r or 'Direct', "count": cnt} for r, cnt in referrer_stats] if referrer_stats else "—"

    data = {
        "store name": link_data["store_name"],
        "item name": link_data["item_name"],
        "total clicks": str(total_clicks),
        "latest click": latest_click.isoformat()[:10] if latest_click else "—",
        "top countries": {"value": top_countries, "is_list": True} if top_countries != "—" else "—",
        "top referrers": {"value": top_referrers, "is_list": True} if top_referrers != "—" else "—"
    }
        
    inspect_table = get_inspect_table("clicks", data)
    
    return render_template(
        "admin/components/_inspect.html",
        inspect_table=inspect_table,
        actions=[]
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

    display_items = []
    for r in serialized:
        display_items.append({
            "id": r["id"],
            "target": r["target_title"],
            "target_type": r["target_icon"],
            "reaction_type": r["type"],
            "date": r["created_at"][:10] if r["created_at"] else "—",
            "username": r["username"],
        })

    html = render_template("admin/components/_rows.html", items=display_items, domain_type="reaction", hide_action_column=True)
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


@bp.route("/views/rows", methods=["GET"])
def views_rows():
    """Return server-rendered HTML rows partial for views AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    start_date = request.args.get("views_start_date", "").strip()
    end_date   = request.args.get("views_end_date", "").strip()
    search     = request.args.get("search", "").strip()

    data = get_admin_views_page(page, per_page, search, start_date, end_date)

    serialized = []
    for v in data["items"]:
        serialized.append({
            "id": f"{v['target_type']}-{v['target_id']}",
            "target": v["target_title"],
            "target_type": v["target_type"],
            "total-views": "{:,}".format(v["view_count"] or 0),
            "auth-views": "{:,}".format(v["auth_views"] or 0),
            "anon-views": "{:,}".format(v["anon_views"] or 0),
            "date": v["latest_view"][:10] if v["latest_view"] else "—"
        })

    html = render_template("admin/components/_rows.html", items=serialized, domain_type="view", hide_action_column=True)
    return make_rows_response(html, total=data["total"], pages=data["pages"], page=data["page"])


@bp.route("/clicks/rows", methods=["GET"])
def clicks_rows():
    """Return server-rendered HTML rows partial for clicks AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    destination = request.args.get("clicks_destination", request.args.get("destination", "")).strip()

    data = get_admin_clicks_page(page, per_page, search, destination)

    serialized = [{
        "id": r["link_id"],
        "name": r["item_name"],
        "store-name": {"name": r["store_name"], "url": r["affiliate_url"]},
        "click-count": "{:,}".format(r["click_count"] or 0),
        "date": r["latest_click"][:10] if r["latest_click"] else "—",
    } for r in data["items"]]

    for d in serialized:
        d["link"] = d.pop("store-name")

    html = render_template("admin/components/_rows.html", items=serialized, domain_type="click", hide_action_column=False)
    return make_rows_response(html, total=data["total"], pages=data["pages"], page=data["page"])


@bp.route("/saves/rows", methods=["GET"])
def saves_rows():
    """Return server-rendered HTML rows partial for saves AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    user_search = request.args.get("saves_user", request.args.get("user", "")).strip()

    pagination, serialized = get_admin_saves_page(
        page, per_page, search, user_search
    )

    display_items = []
    for s in serialized:
        display_items.append({
            "id": s["id"],
            "target": s["target_title"],
            "target_type": s["target_type"],
            "username": s["user_name"],
            "date": s["created_at"][:10] if s["created_at"] else "—",
        })

    html = render_template("admin/components/_rows.html", items=display_items, domain_type="save", hide_action_column=True)
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
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

    display_items = []
    for s in serialized:
        display_items.append({
            "id": s["id"],
            "user": s["user_name"],
            "target": f"{s['target_type'].title()}: {s['target_title']}",
            "channel": s["channel"],
            "date": s["created_at"][:10] if s["created_at"] else "—"
        })

    html = render_template("admin/components/_rows.html", items=display_items, domain_type="share", hide_action_column=True)
    return make_rows_response(html, total=pagination.total, pages=pagination.pages, page=pagination.page)


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
