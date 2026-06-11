# app/admin/recommendations.py
from flask import Blueprint, jsonify, request
from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.item.models import Item
from app.domains.relationships import content_items
from sqlalchemy import select, func

bp = Blueprint("api_recommendation", __name__, url_prefix="/admin/recommendations")


@bp.route("/stats", methods=["GET"])
def recommendation_stats():
    """Aggregate stats for content-item matches."""
    total_matches = db.session.execute(
        select(func.count()).select_from(content_items)
    ).scalar() or 0

    # Count unique contents with at least one linked item
    linked_contents = db.session.execute(
        select(func.count(func.distinct(content_items.c.content_id)))
    ).scalar() or 0

    # Count unique items that appear in at least one match
    linked_items = db.session.execute(
        select(func.count(func.distinct(content_items.c.item_id)))
    ).scalar() or 0

    return jsonify({
        "total_matches": total_matches,
        "linked_contents": linked_contents,
        "linked_items": linked_items,
    })


@bp.route("/matches", methods=["GET"])
def list_matches():
    """Paginated list of content-item associations for admin inspection."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search = request.args.get("search", "").strip()

    # Join content_items with Content and Item tables
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
        stmt = stmt.where(
            Content.title.ilike(like) | Item.name.ilike(like)
        )

    # Manual pagination (content_items is a raw table, not a mapped model)
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.session.execute(total_stmt).scalar() or 0
    pages = max(1, (total + per_page - 1) // per_page)

    stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    rows = db.session.execute(stmt).mappings().all()

    return jsonify({
        "items": [{
            "content_id": r["content_id"],
            "item_id": r["item_id"],
            "content_title": r["content_title"] or f"Content #{r['content_id']}",
            "content_type": r["content_type"],
            "content_views": r["content_views"] or 0,
            "item_name": r["item_name"] or f"Item #{r['item_id']}",
            "item_type": r["item_type"],
            "item_clicks": r["item_clicks"] or 0,
        } for r in rows],
        "page": page,
        "pages": pages,
        "total": total,
        "per_page": per_page,
    })


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
