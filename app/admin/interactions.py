# app/admin/interactions.py
"""
Admin interaction management endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- Interaction stats endpoint reads from the 60-second cached
  get_interactions_breakdown() instead of issuing 8 independent queries (R-03).
- All queries use modern select() style (R-07).
- Shared pagination helpers from app.admin.helpers (R-18, R-21).
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
from app.domains.user.models import User
from app.admin.helpers import parse_pagination_params, make_rows_response
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

    stmt = select(Comment).order_by(Comment.id.desc())
    if user_search:
        stmt = stmt.join(User, Comment.user_id == User.id)
    if sentiment:
        stmt = stmt.where(Comment.sentiment == sentiment)
    if target_type:
        stmt = stmt.where(Comment.target_type == target_type)
    if search:
        stmt = stmt.where(Comment.content.ilike(f"%{search}%"))
    if user_search:
        stmt = stmt.where(
            or_(User.name.ilike(f"%{user_search}%"), User.email.ilike(f"%{user_search}%"))
        )
    if start_date:
        try:
            from datetime import date, datetime
            stmt = stmt.where(Comment.created_at >= datetime.combine(date.fromisoformat(start_date), datetime.min.time()))
        except ValueError:
            pass
    if end_date:
        try:
            from datetime import date, datetime
            stmt = stmt.where(Comment.created_at <= datetime.combine(date.fromisoformat(end_date), datetime.max.time()))
        except ValueError:
            pass

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    users, content_titles, item_names = _load_interaction_context(pagination.items)

    serialized = []
    for c in pagination.items:
        user = users.get(c.user_id)
        target_title = (
            content_titles.get(c.target_id)
            if c.target_type == "content"
            else item_names.get(c.target_id)
        )
        serialized.append({
            "id":           c.id,
            "content":      c.content,
            "preview":      c.content[:120] + ("…" if len(c.content) > 120 else ""),
            "user_id":      c.user_id,
            "user_name":    user["name"] if user else f"User #{c.user_id}",
            "user_email":   user["email"] if user else None,
            "parent_id":    c.parent_id,
            "sentiment":    c.sentiment or "neutral",
            "confidence":   c.confidence,
            "target_type":  c.target_type,
            "target_id":    c.target_id,
            "target_title": target_title or f"{c.target_type.capitalize()} #{c.target_id}",
            "like_count":   c.like_count,
            "replies_count": c.replies_count,
            "created_at":   c.created_at.isoformat() if c.created_at else None,
        })

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
    comment = db.session.get(Comment, id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"success": True, "message": "Comment deleted."})


@bp.route("/comments/<int:id>/flag", methods=["POST"])
def flag_comment(id):
    """Flag a comment as spam by marking its sentiment."""
    comment = db.session.get(Comment, id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404
    comment.sentiment = "spam"
    db.session.commit()
    return jsonify({"success": True, "message": "Comment flagged as spam."})


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

    stmt = select(Reaction).order_by(Reaction.id.desc())
    if reaction_type:
        stmt = stmt.where(Reaction.type == reaction_type)

    from app.domains.content.models import Content
    from app.domains.item.models import Item

    stmt = stmt.outerjoin(Content, (Reaction.target_id == Content.id) & (Reaction.target_type == "content"))
    stmt = stmt.outerjoin(Item, (Reaction.target_id == Item.id) & (Reaction.target_type == "item"))
    stmt = stmt.join(User, Reaction.user_id == User.id)

    if target:
        stmt = stmt.where(
            or_(
                Content.title.ilike(f"%{target}%"),
                Item.name.ilike(f"%{target}%")
            )
        )
    if user_search:
        stmt = stmt.where(
            or_(
                User.name.ilike(f"%{user_search}%"),
                User.email.ilike(f"%{user_search}%")
            )
        )

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    users, content_titles, item_names = _load_interaction_context(pagination.items)
    
    comment_ids = {r.target_id for r in pagination.items if r.target_type == "comment"}
    comment_previews = {}
    if comment_ids:
        rows = db.session.execute(
            select(Comment.id, Comment.content).where(Comment.id.in_(comment_ids))
        ).mappings().all()
        comment_previews = {r["id"]: r["content"][:60] + ("…" if len(r["content"]) > 60 else "") for r in rows}

    serialized = []
    for r in pagination.items:
        user = users.get(r.user_id)
        if r.target_type == "content":
            target_title = content_titles.get(r.target_id)
        elif r.target_type == "item":
            target_title = item_names.get(r.target_id)
        else:
            target_title = comment_previews.get(r.target_id)

        serialized.append({
            "id":          r.id,
            "type":        r.type,
            "user_id":     r.user_id,
            "username":   user["name"] if user else f"User #{r.user_id}",
            "user_email":  user["email"] if user else None,
            "target_type": r.target_type,
            "target_id":   r.target_id,
            "target_title": target_title or f"{r.target_type.capitalize()} #{r.target_id}",
            "created_at":  r.created_at.isoformat() if r.created_at else None,
        })

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

    stmt = (
        select(
            View.target_type,
            View.target_id,
            func.count(View.id).label("view_count"),
            func.max(View.created_at).label("latest_view")
        )
        .select_from(View)
    )

    from app.domains.content.models import Content
    from app.domains.item.models import Item

    stmt = stmt.outerjoin(Content, (View.target_id == Content.id) & (View.target_type == "content"))
    stmt = stmt.outerjoin(Item, (View.target_id == Item.id) & (View.target_type == "item"))

    if target:
        stmt = stmt.where(
            or_(
                Content.title.ilike(f"%{target}%"),
                Item.name.ilike(f"%{target}%")
            )
        )

    if start_date:
        try:
            from datetime import date
            stmt = stmt.where(View.created_at >= datetime.combine(date.fromisoformat(start_date), datetime.min.time()))
        except ValueError:
            pass
    if end_date:
        try:
            from datetime import date
            stmt = stmt.where(View.created_at <= datetime.combine(date.fromisoformat(end_date), datetime.max.time()))
        except ValueError:
            pass

    stmt = stmt.group_by(View.target_type, View.target_id).order_by(func.max(View.created_at).desc())

    # Manual pagination to prevent scalar mapping issue
    total = db.session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    paginated_stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    items = db.session.execute(paginated_stmt).all()

    content_titles, item_names = _load_target_titles(items)

    import math
    pages = math.ceil(total / per_page) if per_page > 0 else 1

    serialized = []
    for v in items:
        target_title = (
            content_titles.get(v.target_id)
            if v.target_type == "content"
            else item_names.get(v.target_id)
        )
        serialized.append({
            "target_type": v.target_type,
            "target_id": v.target_id,
            "target_title": target_title or f"{v.target_type.capitalize()} #{v.target_id}",
            "view_count": v.view_count,
            "created_at": v.latest_view.isoformat() if v.latest_view else None
        })

    return jsonify({
        "items":    serialized,
        "page":     page,
        "pages":    pages,
        "total":    total,
        "per_page": per_page,
    })


@bp.route("/clicks", methods=["GET"])
def list_clicks():
    """Paginated click logs aggregated by external link."""
    page, per_page = parse_pagination_params(default_per_page=25)
    target = request.args.get("search", "").strip()
    destination = request.args.get("clicks_destination", request.args.get("destination", "")).strip()

    from app.domains.item.models import ItemStoreLink, ItemVariant, Item, Store

    stmt = (
        select(
            ItemStoreLink.id.label("link_id"),
            ItemStoreLink.affiliate_url,
            Store.name.label("store_name"),
            Item.id.label("item_id"),
            Item.name.label("item_name"),
            func.count(ItemClick.id).label("click_count"),
            func.max(ItemClick.created_at).label("latest_click")
        )
        .select_from(ItemClick)
        .join(ItemStoreLink, ItemClick.item_store_link_id == ItemStoreLink.id)
        .join(Store, ItemStoreLink.store_id == Store.id)
        .join(ItemVariant, ItemStoreLink.variant_id == ItemVariant.id)
        .join(Item, ItemVariant.item_id == Item.id)
    )

    if target:
        stmt = stmt.where(Item.name.ilike(f"%{target}%"))
    if destination:
        if destination.isdigit():
            stmt = stmt.where(Store.id == int(destination))
        else:
            stmt = stmt.where(Store.name.ilike(f"%{destination}%"))

    stmt = stmt.group_by(
        ItemStoreLink.id,
        ItemStoreLink.affiliate_url,
        Store.name,
        Item.id,
        Item.name
    ).order_by(func.max(ItemClick.created_at).desc())

    # Manual pagination to prevent scalar mapping issue
    total = db.session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    paginated_stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    items = db.session.execute(paginated_stmt).all()

    import math
    pages = math.ceil(total / per_page) if per_page > 0 else 1

    serialized = []
    for row in items:
        serialized.append({
            "link_id": row.link_id,
            "affiliate_url": row.affiliate_url,
            "store_name": row.store_name,
            "item_id": row.item_id,
            "item_name": row.item_name,
            "click_count": row.click_count,
            "created_at": row.latest_click.isoformat() if row.latest_click else None
        })

    return jsonify({
        "items":    serialized,
        "page":     page,
        "pages":    pages,
        "total":    total,
        "per_page": per_page,
    })



@bp.route("/saves", methods=["GET"])
def list_saves():
    """Paginated list of saves with user and target details."""
    page, per_page = parse_pagination_params(default_per_page=25)
    target = request.args.get("search", "").strip()
    user_search = request.args.get("saves_user", request.args.get("user", "")).strip()

    stmt = select(Save).order_by(Save.id.desc())

    from app.domains.content.models import Content
    from app.domains.item.models import Item

    stmt = stmt.outerjoin(Content, (Save.target_id == Content.id) & (Save.target_type == "content"))
    stmt = stmt.outerjoin(Item, (Save.target_id == Item.id) & (Save.target_type == "item"))
    stmt = stmt.join(User, Save.user_id == User.id)

    if target:
        stmt = stmt.where(
            or_(
                Content.title.ilike(f"%{target}%"),
                Item.name.ilike(f"%{target}%")
            )
        )
    if user_search:
        stmt = stmt.where(
            or_(
                User.name.ilike(f"%{user_search}%"),
                User.email.ilike(f"%{user_search}%")
            )
        )

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    users, content_titles, item_names = _load_interaction_context(pagination.items)

    serialized = []
    for s in pagination.items:
        user = users.get(s.user_id)
        target_title = (
            content_titles.get(s.target_id)
            if s.target_type == "content"
            else item_names.get(s.target_id)
        )
        serialized.append({
            "id": s.id,
            "user_id": s.user_id,
            "user_name": user["name"] if user else f"User #{s.user_id}",
            "user_email": user["email"] if user else None,
            "target_type": s.target_type,
            "target_id": s.target_id,
            "target_title": target_title or f"{s.target_type.capitalize()} #{s.target_id}",
            "created_at": s.created_at.isoformat() if s.created_at else None
        })

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

    stmt = select(Share).order_by(Share.id.desc())

    from app.domains.content.models import Content
    from app.domains.item.models import Item

    stmt = stmt.outerjoin(Content, (Share.target_id == Content.id) & (Share.target_type == "content"))
    stmt = stmt.outerjoin(Item, (Share.target_id == Item.id) & (Share.target_type == "item"))
    stmt = stmt.join(User, Share.user_id == User.id)

    if target:
        stmt = stmt.where(
            or_(
                Content.title.ilike(f"%{target}%"),
                Item.name.ilike(f"%{target}%")
            )
        )
    if user_search:
        stmt = stmt.where(
            or_(
                User.name.ilike(f"%{user_search}%"),
                User.email.ilike(f"%{user_search}%")
            )
        )

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    users, content_titles, item_names = _load_interaction_context(pagination.items)

    serialized = []
    for s in pagination.items:
        user = users.get(s.user_id)
        target_title = (
            content_titles.get(s.target_id)
            if s.target_type == "content"
            else item_names.get(s.target_id)
        )
        serialized.append({
            "id": s.id,
            "user_id": s.user_id,
            "user_name": user["name"] if user else f"User #{s.user_id}",
            "user_email": user["email"] if user else None,
            "target_type": s.target_type,
            "target_id": s.target_id,
            "target_title": target_title or f"{s.target_type.capitalize()} #{s.target_id}",
            "channel": s.channel or "—",
            "created_at": s.created_at.isoformat() if s.created_at else None
        })

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

    stmt = select(Comment).order_by(Comment.id.desc())
    if user_search:
        stmt = stmt.join(User, Comment.user_id == User.id)
    if sentiment:   stmt = stmt.where(Comment.sentiment == sentiment)
    if target_type: stmt = stmt.where(Comment.target_type == target_type)
    if search:      stmt = stmt.where(Comment.content.ilike(f"%{search}%"))
    if user_search:
        stmt = stmt.where(
            or_(User.name.ilike(f"%{user_search}%"), User.email.ilike(f"%{user_search}%"))
        )
    if start_date:
        try:
            from datetime import date, datetime
            stmt = stmt.where(Comment.created_at >= datetime.combine(date.fromisoformat(start_date), datetime.min.time()))
        except ValueError:
            pass
    if end_date:
        try:
            from datetime import date, datetime
            stmt = stmt.where(Comment.created_at <= datetime.combine(date.fromisoformat(end_date), datetime.max.time()))
        except ValueError:
            pass

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    users, content_titles, item_names = _load_interaction_context(pagination.items)
    serialized = [_serialize_comment(c, users, content_titles, item_names) for c in pagination.items]

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
    from app.domains.interaction.service.inspect import get_comment_inspect_metrics
    metrics = get_comment_inspect_metrics(id)
    
    if not metrics:
        return None
        
    comment = metrics["comment"]
    total_user_comments = metrics["total_user_comments"]
    target_sentiments = metrics["target_sentiments"]
    recent_reactions = metrics["recent_reactions"]
    
    from app.admin.tables import get_inspect_table
    
    target_title = comment.target.title if comment.target_type == 'content' and comment.target else (comment.target.name if comment.target else f"{comment.target_type.capitalize()} #{comment.target_id}")
    
    parent_context = "—"
    if comment.parent:
        parent_context = comment.parent.content[:60] + ("…" if len(comment.parent.content) > 60 else "")

    latest_replies = "—"
    if comment.replies:
        sorted_replies = sorted(comment.replies, key=lambda r: r.created_at, reverse=True)
        latest_replies = [{"label": f"• {r.content[:40]}..."} for r in sorted_replies[:3]]

    total_target_comments = sum(count for _, count in target_sentiments)
    sentiment_dist = []
    for sentiment, count in target_sentiments:
        pct = (count / total_target_comments * 100) if total_target_comments > 0 else 0
        s_label = sentiment.title() if sentiment else 'Neutral'
        sentiment_dist.append({"label": s_label, "count": f"{count} ({pct:.1f}%)"})
    
    reactions_html = "—"
    if recent_reactions:
        reactions_html = [{"label": r.user.name if r.user else 'User', "detail": r.type.title()} for r in recent_reactions]

    data = {
        "id": f"#{comment.id}",
        "comment": comment.content,
        "sentiment": comment.sentiment or "neutral",
        "confidence": str(round(comment.confidence, 2)) if comment.confidence else "—",
        "likes": "{:,}".format(comment.like_count),
        "dislikes": "{:,}".format(comment.dislike_count),
        "shares": "{:,}".format(comment.share_count),
        "replies count": str(comment.replies_count),
        "recent reactions": {"value": reactions_html, "is_list": True} if reactions_html != "—" else "—",
        
        "user id": str(comment.user_id),
        "user name": comment.user.name if comment.user else "—",
        "user email": comment.user.email if comment.user else "—",
        "total comments": str(total_user_comments),
        
        "parent context": parent_context,
        "latest replies": {"value": latest_replies, "is_list": True} if latest_replies != "—" else "—",
        
        "target type": comment.target_type,
        "target title": target_title,
        "date": comment.created_at.isoformat()[:10] if comment.created_at else "—",
        "target comments": str(total_target_comments),
        "sentiment distribution": {"value": sentiment_dist, "is_list": True} if sentiment_dist else "—"
    }
    inspect_table = get_inspect_table("comments", data)

    actions = [
        {
            "label": "Already Flagged" if comment.sentiment == 'spam' else "Flag as Spam",
            "action_type": "toggle-active",
            "icon": "🚩",
            "disabled": True if comment.sentiment == 'spam' else False,
            "attrs": {"data-action": "flag-comment", "data-id": comment.id}
        },
        {
            "label": "Delete Comment",
            "action_type": "delete",
            "icon": "🗑",
            "extra_class": "inspect-delete-btn",
            "attrs": {"data-action": "delete-comment", "data-id": comment.id}
        }
    ]

    return {
        "inspect_table": inspect_table,
        "actions": actions,
        "inspect_id": comment.id
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

    from app.admin.tables import get_inspect_table
    
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

    stmt = select(Reaction).order_by(Reaction.id.desc())
    if reaction_type: stmt = stmt.where(Reaction.type == reaction_type)
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    user_ids = {r.user_id for r in pagination.items}
    users = {}
    if user_ids:
        rows = db.session.execute(select(User.id, User.name, User.email).where(User.id.in_(user_ids))).mappings().all()
        users = {r["id"]: r for r in rows}

    content_titles, item_names = _load_target_titles(pagination.items)

    comment_ids = {r.target_id for r in pagination.items if r.target_type == "comment"}
    comment_previews = {}
    if comment_ids:
        rows = db.session.execute(
            select(Comment.id, Comment.content).where(Comment.id.in_(comment_ids))
        ).mappings().all()
        comment_previews = {r["id"]: r["content"][:60] + ("…" if len(r["content"]) > 60 else "") for r in rows}

    serialized = []
    for r in pagination.items:
        user = users.get(r.user_id)
        if r.target_type == "content":
            tt = content_titles.get(r.target_id)
            icon = "📄 Content"
        elif r.target_type == "item":
            tt = item_names.get(r.target_id)
            icon = "📦 Item"
        else:
            tt = comment_previews.get(r.target_id)
            icon = "💬 Comment"

        serialized.append({
            "id": r.id,
            "target": tt or f"{r.target_type.capitalize()} #{r.target_id}",
            "target_type": icon,
            "reaction_type": r.type,
            "date": r.created_at.isoformat()[:10] if r.created_at else "—",
            "username": user["name"] if user else f"User #{r.user_id}",
        })

    html = render_template("admin/components/_rows.html", items=serialized, domain_type="reaction", hide_action_column=True)
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

    from sqlalchemy import case
    stmt = (
        select(
            View.target_type,
            View.target_id,
            func.count(View.id).label("view_count"),
            func.sum(case((View.user_id.isnot(None), 1), else_=0)).label("auth_views"),
            func.sum(case((View.user_id.is_(None), 1), else_=0)).label("anon_views"),
            func.max(View.created_at).label("latest_view")
        )
        .select_from(View)
    )

    from app.domains.content.models import Content
    from app.domains.item.models import Item

    stmt = stmt.outerjoin(Content, (View.target_id == Content.id) & (View.target_type == "content"))
    stmt = stmt.outerjoin(Item, (View.target_id == Item.id) & (View.target_type == "item"))

    if search:
        stmt = stmt.where(
            or_(
                Content.title.ilike(f"%{search}%"),
                Item.name.ilike(f"%{search}%")
            )
        )

    if start_date:
        try:
            from datetime import date
            stmt = stmt.where(View.created_at >= datetime.combine(date.fromisoformat(start_date), datetime.min.time()))
        except ValueError:
            pass
    if end_date:
        try:
            from datetime import date
            stmt = stmt.where(View.created_at <= datetime.combine(date.fromisoformat(end_date), datetime.max.time()))
        except ValueError:
            pass

    stmt = stmt.group_by(View.target_type, View.target_id).order_by(func.max(View.created_at).desc())

    total = db.session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    paginated_stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    items = db.session.execute(paginated_stmt).all()

    content_titles, item_names = _load_target_titles(items)

    import math
    pages = math.ceil(total / per_page) if per_page > 0 else 1

    serialized = []
    for v in items:
        target_title = (
            content_titles.get(v.target_id)
            if v.target_type == "content"
            else item_names.get(v.target_id)
        )
        serialized.append({
            "id": f"{v.target_type}-{v.target_id}",
            "target": target_title or f"{v.target_type.capitalize()} #{v.target_id}",
            "target_type": v.target_type,
            "total-views": "{:,}".format(v.view_count or 0),
            "auth-views": "{:,}".format(v.auth_views or 0),
            "anon-views": "{:,}".format(v.anon_views or 0),
            "date": v.latest_view.isoformat()[:10] if v.latest_view else "—"
        })

    html = render_template("admin/components/_rows.html", items=serialized, domain_type="view", hide_action_column=True)
    return make_rows_response(html, total=total, pages=pages, page=page)


@bp.route("/clicks/rows", methods=["GET"])
def clicks_rows():
    """Return server-rendered HTML rows partial for clicks AJAX injection."""
    from app.domains.item.models import Item, ItemVariant, ItemStoreLink, Store
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    destination = request.args.get("clicks_destination", request.args.get("destination", "")).strip()

    stmt = (
        select(
            ItemStoreLink.id.label("link_id"),
            Item.name.label("item_name"),
            Store.name.label("store_name"),
            ItemStoreLink.affiliate_url,
            func.count(ItemClick.id).label("click_count"),
            func.max(ItemClick.created_at).label("created_at"),
        )
        .join(ItemStoreLink, ItemStoreLink.id == ItemClick.item_store_link_id)
        .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
        .join(Item, Item.id == ItemVariant.item_id)
        .join(Store, Store.id == ItemStoreLink.store_id)
        .group_by(ItemStoreLink.id, Item.id, Store.id, ItemStoreLink.affiliate_url)
        .order_by(func.count(ItemClick.id).desc())
    )
    if search:
        stmt = stmt.where(or_(Item.name.ilike(f"%{search}%"), Store.name.ilike(f"%{search}%")))
    if destination:
        if destination.isdigit():
            stmt = stmt.where(Store.id == int(destination))
        else:
            stmt = stmt.where(Store.name.ilike(f"%{destination}%"))

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.session.execute(total_stmt).scalar() or 0
    stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    rows = db.session.execute(stmt).mappings().all()

    pages = max(1, (total + per_page - 1) // per_page)
    serialized = [{
        "id": r["link_id"],
        "name": r["item_name"],
        "store-name": {"name": r["store_name"], "url": r["affiliate_url"]},
        "click-count": "{:,}".format(r["click_count"] or 0),
        "date": r["created_at"].isoformat()[:10] if r["created_at"] else "—",
    } for r in rows]

    # Map the store_name back to link format if we wanted, but _rows.html uses 'link' key explicitly for URLs.
    # Wait, 'link' key uses <a>, but the column name will be 'link'. Let's rename the key to 'link'.
    for d in serialized:
        d["link"] = d.pop("store_name")

    html = render_template("admin/components/_rows.html", items=serialized, domain_type="click", hide_action_column=False)
    return make_rows_response(html, total=total, pages=pages, page=page)


@bp.route("/saves/rows", methods=["GET"])
def saves_rows():
    """Return server-rendered HTML rows partial for saves AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    user_search = request.args.get("saves_user", request.args.get("user", "")).strip()

    stmt = select(Save).order_by(Save.id.desc())

    from app.domains.content.models import Content
    from app.domains.item.models import Item

    stmt = stmt.outerjoin(Content, (Save.target_id == Content.id) & (Save.target_type == "content"))
    stmt = stmt.outerjoin(Item, (Save.target_id == Item.id) & (Save.target_type == "item"))
    stmt = stmt.join(User, Save.user_id == User.id)

    if search:
        stmt = stmt.where(
            or_(
                Content.title.ilike(f"%{search}%"),
                Item.name.ilike(f"%{search}%")
            )
        )
    if user_search:
        stmt = stmt.where(
            or_(
                User.name.ilike(f"%{user_search}%"),
                User.email.ilike(f"%{user_search}%")
            )
        )

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    user_ids = {s.user_id for s in pagination.items}
    users = {}
    if user_ids:
        rows = db.session.execute(select(User.id, User.name, User.email).where(User.id.in_(user_ids))).mappings().all()
        users = {r["id"]: r for r in rows}

    content_titles, item_names = _load_target_titles(pagination.items)

    serialized = []
    for s in pagination.items:
        user = users.get(s.user_id)
        tt = content_titles.get(s.target_id) if s.target_type == "content" else item_names.get(s.target_id)
        serialized.append({
            "id": s.id,
            "target": tt or f"{s.target_type.capitalize()} #{s.target_id}",
            "target_type": s.target_type,
            "username": user["name"] if user else f"User #{s.user_id}",
            "date": s.created_at.isoformat()[:10] if s.created_at else "—",
        })

    html = render_template("admin/components/_rows.html", items=serialized, domain_type="save", hide_action_column=True)
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

    stmt = select(Share).order_by(Share.id.desc())

    from app.domains.content.models import Content
    from app.domains.item.models import Item

    stmt = stmt.outerjoin(Content, (Share.target_id == Content.id) & (Share.target_type == "content"))
    stmt = stmt.outerjoin(Item, (Share.target_id == Item.id) & (Share.target_type == "item"))
    stmt = stmt.join(User, Share.user_id == User.id)

    if search:
        stmt = stmt.where(
            or_(
                Content.title.ilike(f"%{search}%"),
                Item.name.ilike(f"%{search}%")
            )
        )
    if user_search:
        stmt = stmt.where(
            or_(
                User.name.ilike(f"%{user_search}%"),
                User.email.ilike(f"%{user_search}%")
            )
        )

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    users, content_titles, item_names = _load_interaction_context(pagination.items)

    serialized = []
    for s in pagination.items:
        user = users.get(s.user_id)
        target_title = (
            content_titles.get(s.target_id)
            if s.target_type == "content"
            else item_names.get(s.target_id)
        )
        serialized.append({
            "id": s.id,
            "user": user["name"] if user else f"User #{s.user_id}",
            "target": f"{s.target_type.title()}: {target_title or s.target_id}",
            "channel": s.channel or "—",
            "date": s.created_at.isoformat()[:10] if s.created_at else "—"
        })

    html = render_template("admin/components/_rows.html", items=serialized, domain_type="share", hide_action_column=True)
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
