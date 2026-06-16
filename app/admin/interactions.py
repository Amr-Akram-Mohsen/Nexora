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

    stmt = select(Comment).order_by(Comment.id.desc())
    if sentiment:
        stmt = stmt.where(Comment.sentiment == sentiment)
    if target_type:
        stmt = stmt.where(Comment.target_type == target_type)
    if search:
        stmt = stmt.where(Comment.content.ilike(f"%{search}%"))

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    # Batch-load user info
    user_ids = {c.user_id for c in pagination.items}
    users = {}
    if user_ids:
        rows = db.session.execute(
            select(User.id, User.name, User.email).where(User.id.in_(user_ids))
        ).mappings().all()
        users = {r["id"]: r for r in rows}

    # Batch-load target titles
    content_ids = {c.target_id for c in pagination.items if c.target_type == "content"}
    item_ids    = {c.target_id for c in pagination.items if c.target_type == "item"}
    content_titles = {}
    item_names     = {}

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

    # Batch user info
    user_ids = {r.user_id for r in pagination.items}
    users = {}
    if user_ids:
        rows = db.session.execute(
            select(User.id, User.name, User.email).where(User.id.in_(user_ids))
        ).mappings().all()
        users = {r["id"]: r for r in rows}

    content_ids = {r.target_id for r in pagination.items if r.target_type == "content"}
    item_ids = {r.target_id for r in pagination.items if r.target_type == "item"}
    comment_ids = {r.target_id for r in pagination.items if r.target_type == "comment"}
    content_titles = {}
    item_names = {}
    comment_previews = {}

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
            "user_name":   user["name"] if user else f"User #{r.user_id}",
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

    content_ids = {v.target_id for v in items if v.target_type == "content"}
    item_ids = {v.target_id for v in items if v.target_type == "item"}
    content_titles = {}
    item_names = {}

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

    user_ids = {s.user_id for s in pagination.items}
    users = {}
    if user_ids:
        rows = db.session.execute(
            select(User.id, User.name, User.email).where(User.id.in_(user_ids))
        ).mappings().all()
        users = {r["id"]: r for r in rows}

    content_ids = {s.target_id for s in pagination.items if s.target_type == "content"}
    item_ids = {s.target_id for s in pagination.items if s.target_type == "item"}
    content_titles = {}
    item_names = {}

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
        "target_title": target_title or f"{c.target_type.capitalize()} #{c.target_id}",
        "created_at":   c.created_at.isoformat() if c.created_at else None,
    }


def _load_comment_context(items):
    """Batch-load user info and target titles for a list of comments."""
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

    stmt = select(Comment).order_by(Comment.id.desc())
    if sentiment:   stmt = stmt.where(Comment.sentiment == sentiment)
    if target_type: stmt = stmt.where(Comment.target_type == target_type)
    if search:      stmt = stmt.where(Comment.content.ilike(f"%{search}%"))

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    users, content_titles, item_names = _load_comment_context(pagination.items)
    serialized = [_serialize_comment(c, users, content_titles, item_names) for c in pagination.items]

    html = render_template("admin/control_panel/interactions/comments/_rows.html", items=serialized)
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


@bp.route("/comments/<int:id>/inspect", methods=["GET"])
def inspect_comment(id):
    """Return server-rendered HTML for the comment inspect modal body."""
    comment = db.session.get(Comment, id)
    if not comment:
        return "<p class='text-muted'>Comment not found.</p>", 404
    users, content_titles, item_names = _load_comment_context([comment])
    data = _serialize_comment(comment, users, content_titles, item_names)
    return render_template("admin/control_panel/interactions/comments/_inspect.html", comment=data)


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

    serialized = []
    for r in pagination.items:
        user = users.get(r.user_id)
        tt = content_titles.get(r.target_id) if r.target_type == "content" else item_names.get(r.target_id)
        serialized.append({
            "id": r.id, "type": r.type, "target_type": r.target_type, "target_id": r.target_id,
            "target_title": tt or f"{r.target_type.capitalize()} #{r.target_id}",
            "user_name": user["name"] if user else f"User #{r.user_id}",
            "user_email": user["email"] if user else "",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    html = render_template("admin/control_panel/interactions/reactions/_rows.html", items=serialized)
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

    content_ids = {v.target_id for v in items if v.target_type == "content"}
    item_ids = {v.target_id for v in items if v.target_type == "item"}
    content_titles = {}
    item_names = {}

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
            "view_count": v.view_count or 0,
            "created_at": v.latest_view.isoformat() if v.latest_view else None
        })

    html = render_template("admin/control_panel/interactions/views/_rows.html", items=serialized)
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
        .group_by(Item.id, Store.id, ItemStoreLink.affiliate_url)
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
        "item_name": r["item_name"], "store_name": r["store_name"],
        "affiliate_url": r["affiliate_url"],
        "click_count": r["click_count"] or 0,
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
    } for r in rows]

    html = render_template("admin/control_panel/interactions/clicks/_rows.html", items=serialized)
    return make_rows_response(html, total=total, pages=pages, page=page)


@bp.route("/saves/rows", methods=["GET"])
def saves_rows():
    """Return server-rendered HTML rows partial for saves AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search      = request.args.get("search", "").strip()

    stmt = select(Save).order_by(Save.id.desc())
    if search: stmt = stmt.where(Save.target_type.ilike(f"%{search}%"))
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
            "target_title": tt or f"{s.target_type.capitalize()} #{s.target_id}",
            "target_type": s.target_type,
            "user_name": user["name"] if user else f"User #{s.user_id}",
            "user_email": user["email"] if user else "",
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    html = render_template("admin/control_panel/interactions/saves/_rows.html", items=serialized)
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
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
