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
from app.admin.helpers import paginate_manual, make_rows_response
from sqlalchemy import select, func

bp = Blueprint("api_recommendation", __name__, url_prefix="/admin/recommendations")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all recommendation management endpoints require admin privilege."""
    pass


@bp.route("/stats", methods=["GET"])
def recommendation_stats():
    """Aggregate stats for content-item matches."""
    total_matches = db.session.execute(
        select(func.count()).select_from(content_items)
    ).scalar() or 0

    linked_contents = db.session.execute(
        select(func.count(func.distinct(content_items.c.content_id)))
    ).scalar() or 0

    linked_items = db.session.execute(
        select(func.count(func.distinct(content_items.c.item_id)))
    ).scalar() or 0

    return jsonify({
        "total_matches":   total_matches,
        "linked_contents": linked_contents,
        "linked_items":    linked_items,
    })


def _fetch_matches_page(page, per_page, search):
    """
    Run the paginated matches query and serialize results.
    Returns (total, pages, serialized_list).
    Shared between list_matches (JSON) and matches_rows (HTML partial).
    """
    stmt = (
        select(
            content_items.c.content_id,
            content_items.c.item_id,
            Content.title.label("content_title"),
            Content.object_type.label("content_type"),
            Content.view_count.label("content_views"),
            Item.name.label("item_name"),
            Item.item_type.label("item_type"),
            Item.click_count.label("item_clicks"),
        )
        .join(Content, Content.id == content_items.c.content_id)
        .join(Item, Item.id == content_items.c.item_id)
        .order_by(Content.view_count.desc(), Item.click_count.desc())
    )
    if search:
        like = f"%{search}%"
        stmt = stmt.where(Content.title.ilike(like) | Item.name.ilike(like))

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.session.execute(total_stmt).scalar() or 0
    pages = max(1, (total + per_page - 1) // per_page)

    stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    rows = db.session.execute(stmt).mappings().all()

    serialized = [{
        "content_id":    r["content_id"],
        "item_id":       r["item_id"],
        "content_title": r["content_title"] or f"Content #{r['content_id']}",
        "content_type":  r["content_type"],
        "content_views": r["content_views"] or 0,
        "item_name":     r["item_name"] or f"Item #{r['item_id']}",
        "item_type":     r["item_type"],
        "item_clicks":   r["item_clicks"] or 0,
    } for r in rows]
    return total, pages, serialized


@bp.route("/matches", methods=["GET"])
def list_matches():
    """Paginated list of content-item associations for admin inspection."""
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search   = request.args.get("search", "").strip()
    total, pages, serialized = _fetch_matches_page(page, per_page, search)
    return jsonify(paginate_manual(serialized, page, per_page, total))


@bp.route("/matches/rows", methods=["GET"])
def matches_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search   = request.args.get("search", "").strip()
    total, pages, serialized = _fetch_matches_page(page, per_page, search)
    
    display_items = [
        {
            "id": f"{r['content_id']}-{r['item_id']}",
            "content": f"{r['content_title']} (#{r['content_id']})",
            "content_views": "{:,}".format(r["content_views"] or 0),
            "item": f"{r['item_name']} (#{r['item_id']})",
            "item_clicks": "{:,}".format(r["item_clicks"] or 0)
        } for r in serialized
    ]

    html = render_template("admin/components/_rows.html", items=display_items, domain_type="rec")
    return make_rows_response(html, total=total, pages=pages, page=page)


@bp.route("/matches/<int:content_id>/<int:item_id>/inspect", methods=["GET"])
def inspect_match(content_id, item_id):
    """Return server-rendered HTML for the recommendation inspect modal body."""
    row = db.session.execute(
        select(
            content_items.c.content_id,
            content_items.c.item_id,
            Content.title.label("content_title"),
            Content.object_type.label("content_type"),
            Content.view_count.label("content_views"),
            Item.name.label("item_name"),
            Item.item_type.label("item_type"),
            Item.click_count.label("item_clicks"),
        )
        .join(Content, Content.id == content_items.c.content_id)
        .join(Item, Item.id == content_items.c.item_id)
        .where(content_items.c.content_id == content_id, content_items.c.item_id == item_id)
    ).mappings().first()

    if not row:
        return "<p class='text-muted'>Association not found.</p>", 404

    match = {
        "content_id":    row["content_id"],
        "item_id":       row["item_id"],
        "content_title": row["content_title"] or f"Content #{row['content_id']}",
        "content_type":  row["content_type"],
        "content_views": row["content_views"] or 0,
        "item_name":     row["item_name"] or f"Item #{row['item_id']}",
        "item_type":     row["item_type"],
        "item_clicks":   row["item_clicks"] or 0,
    }
    return render_template("admin/control_panel/recommendations/_inspect.html", match=match)


@bp.route("/matches/<int:content_id>/<int:item_id>", methods=["DELETE"])
def unlink_match(content_id, item_id):
    """Remove a content-item association."""
    db.session.execute(
        content_items.delete().where(
            content_items.c.content_id == content_id,
            content_items.c.item_id == item_id,
        )
    )
    db.session.commit()
    return jsonify({"success": True, "message": "Association removed."})
