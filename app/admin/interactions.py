# app/admin/interactions.py
from flask import Blueprint, jsonify, request
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.interaction.models import Comment, Reaction, View, Save, Share
from app.domains.interaction.service.query import (
    get_interactions_breakdown,
    get_reaction_stats,
    get_view_stats,
    get_save_stats,
    get_share_stats,
    get_click_stats,
)
from app.domains.user.models import User
from sqlalchemy import select, func, or_

bp = Blueprint("api_interaction", __name__, url_prefix="/admin/interactions")


# ---------------------------
# COMMENTS
# ---------------------------

@bp.route("/comments", methods=["GET"])
def list_comments():
    """Paginated, enriched comment listing with user and target info."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    sentiment = request.args.get("sentiment", "").strip()
    target_type = request.args.get("target_type", "").strip()
    search = request.args.get("search", "").strip()

    stmt = select(Comment).order_by(Comment.id.desc())

    if sentiment:
        stmt = stmt.where(Comment.sentiment == sentiment)
    if target_type:
        stmt = stmt.where(Comment.target_type == target_type)
    if search:
        stmt = stmt.where(Comment.content.ilike(f"%{search}%"))

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    # Batch-load user names
    user_ids = {c.user_id for c in pagination.items}
    users = {}
    if user_ids:
        rows = db.session.execute(
            select(User.id, User.name, User.email).where(User.id.in_(user_ids))
        ).mappings().all()
        users = {r["id"]: r for r in rows}

    # Batch-load target titles
    content_ids = {c.target_id for c in pagination.items if c.target_type == "content"}
    item_ids = {c.target_id for c in pagination.items if c.target_type == "item"}
    content_titles = {}
    item_names = {}

    if content_ids:
        from app.domains.content.models import Content
        rows = db.session.execute(
            select(Content.id, Content.title).where(Content.id.in_(content_ids))
        ).mappings().all()
        content_titles = {r["id"]: r["title"] for r in rows}

    if item_ids:
        from app.domains.item.models import Item
        rows = db.session.execute(
            select(Item.id, Item.name).where(Item.id.in_(item_ids))
        ).mappings().all()
        item_names = {r["id"]: r["name"] for r in rows}

    serialized = []
    for c in pagination.items:
        user = users.get(c.user_id)
        target_title = (
            content_titles.get(c.target_id)
            if c.target_type == "content"
            else item_names.get(c.target_id)
        )
        serialized.append({
            "id": c.id,
            "content": c.content,
            "preview": c.content[:120] + ("…" if len(c.content) > 120 else ""),
            "user_id": c.user_id,
            "user_name": user["name"] if user else f"User #{c.user_id}",
            "user_email": user["email"] if user else None,
            "parent_id": c.parent_id,
            "sentiment": c.sentiment or "neutral",
            "confidence": c.confidence,
            "target_type": c.target_type,
            "target_id": c.target_id,
            "target_title": target_title or f"{c.target_type.capitalize()} #{c.target_id}",
            "like_count": c.like_count,
            "replies_count": c.replies_count,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return jsonify({
        "items": serialized,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/comments/<int:id>", methods=["DELETE"])
@admin_required
def delete_comment(id):
    """Delete a comment and all its replies."""
    comment = db.session.get(Comment, id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    db.session.delete(comment)
    db.session.commit()
    return jsonify({"success": True, "message": "Comment deleted."})


@bp.route("/comments/<int:id>/flag", methods=["POST"])
@admin_required
def flag_comment(id):
    """Flag a comment as spam by marking its sentiment."""
    comment = db.session.get(Comment, id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    comment.sentiment = "spam"
    db.session.commit()
    return jsonify({"success": True, "message": "Comment flagged as spam."})


# ---------------------------
# REACTIONS
# ---------------------------

@bp.route("/reactions", methods=["GET"])
def list_reactions():
    """Paginated reactions list for moderation view."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    reaction_type = request.args.get("type", "").strip()

    stmt = select(Reaction).order_by(Reaction.id.desc())
    if reaction_type:
        stmt = stmt.where(Reaction.type == reaction_type)

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    # Batch user info
    user_ids = {r.user_id for r in pagination.items}
    users = {}
    if user_ids:
        rows = db.session.execute(
            select(User.id, User.name).where(User.id.in_(user_ids))
        ).mappings().all()
        users = {r["id"]: r["name"] for r in rows}

    serialized = [{
        "id": r.id,
        "type": r.type,
        "user_id": r.user_id,
        "user_name": users.get(r.user_id, f"User #{r.user_id}"),
        "target_type": r.target_type,
        "target_id": r.target_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in pagination.items]

    return jsonify({
        "items": serialized,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "per_page": pagination.per_page,
    })


# ---------------------------
# STATS (DASHBOARD)
# ---------------------------

@bp.route("/stats", methods=["GET"])
def interactions_stats():
    """Unified stats endpoint — returns breakdown + total + reaction split."""
    breakdown = get_interactions_breakdown()
    reaction_stats = get_reaction_stats()
    total = sum(breakdown.values())

    return jsonify({
        "comments":   breakdown.get("comments", 0),
        "reactions":  breakdown.get("reactions", 0),
        "views":      breakdown.get("views", 0),
        "saves":      breakdown.get("saves", 0),
        "shares":     breakdown.get("shares", 0),
        "item_clicks": breakdown.get("clicks", 0),
        "likes":      reaction_stats.get("likes", 0),
        "dislikes":   reaction_stats.get("dislikes", 0),
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
