# app/admin/users.py
"""
Admin user management endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- Listing now returns a proper paginated envelope {items, page, pages, total, per_page}
  instead of a flat array limited to 10 results (R-09).
- Normalized to LF line endings (R-24).
- Added /rows HTML partial endpoint and /<id>/inspect HTML endpoint for Jinja AJAX architecture.
"""
from flask import Blueprint, jsonify, request, render_template
from app.domains.user.models import User
from app.domains.user.service import deactivate_user as deactivate_user_service, activate_user as activate_user_service
from app.core.decorators import admin_required
from app.core.extensions import db
from app.admin.helpers import parse_pagination_params, make_rows_response
from sqlalchemy import select, or_, func
from app.domains.taxonomy.models import Category, Topic, Brand
from app.domains.interaction.models import Comment, Reaction, View, Save, ItemClick, RecommendationImpression, RecommendationClick
from app.domains.recommendation.models import UserInterest, UserEntityInterest

bp = Blueprint("api_user", __name__, url_prefix="/admin/users")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all user management endpoints require admin privilege."""
    pass


def _paginate_manual(search, role, page, per_page):
    stmt = _build_user_query(search, role)
    
    # count query
    count_stmt = select(func.count(User.id))
    if search:
        count_stmt = count_stmt.where(
            or_(User.name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
        )
    if role:
        if role.lower() == "admin":
            count_stmt = count_stmt.where(User.is_admin == True)
        elif role.lower() == "user":
            count_stmt = count_stmt.where(User.is_admin == False)
            
    total = db.session.scalar(count_stmt) or 0
    
    # items query
    offset = (page - 1) * per_page
    items_stmt = stmt.limit(per_page).offset(offset)
    items = db.session.execute(items_stmt).all() # returns list of Rows: (User, score)
    
    import math
    pages = math.ceil(total / per_page) if per_page else 1
    return items, total, pages


@bp.route("/", methods=["GET"])
def list_users():
    """Paginated user listing with optional search and role filter."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    role   = request.args.get("role", "").strip()

    items, total, pages = _paginate_manual(search, role, page, per_page)

    serialized = []
    for u, score in items:
        serialized.append({
            "id":         u.id,
            "name":       u.name,
            "email":      u.email,
            "is_admin":   u.is_admin,
            "is_active":  u.is_active,
            "created_at": str(u.created_at),
            "last_login_at": str(u.last_login_at) if u.last_login_at else None,
            "engagement_score": score or 0,
        })

    return jsonify({
        "items":    serialized,
        "page":     page,
        "pages":    pages,
        "total":    total,
        "per_page": per_page,
    })


@bp.route("/<int:id>", methods=["DELETE"])
def delete_user(id):
    success = deactivate_user_service(id)
    if not success:
        return jsonify({"error": "User not found"}), 404
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/<int:id>/activate", methods=["POST"])
def activate_user(id):
    success = activate_user_service(id)
    if not success:
        return jsonify({"error": "User not found"}), 404
    db.session.commit()
    return jsonify({"success": True})


def _build_user_query(search, role):
    """Shared query builder for users listing and rows endpoint."""
    views_sub = select(View.user_id, func.count(View.id).label("cnt")).where(View.user_id.isnot(None)).group_by(View.user_id).subquery()
    clicks_sub = select(ItemClick.user_id, func.count(ItemClick.id).label("cnt")).where(ItemClick.user_id.isnot(None)).group_by(ItemClick.user_id).subquery()
    saves_sub = select(Save.user_id, func.count(Save.id).label("cnt")).group_by(Save.user_id).subquery()
    reactions_sub = select(Reaction.user_id, func.count(Reaction.id).label("cnt")).group_by(Reaction.user_id).subquery()
    comments_sub = select(Comment.user_id, func.count(Comment.id).label("cnt")).group_by(Comment.user_id).subquery()

    engagement_score_expr = (
        func.coalesce(views_sub.c.cnt, 0) * 1 +
        func.coalesce(clicks_sub.c.cnt, 0) * 2 +
        func.coalesce(saves_sub.c.cnt, 0) * 3 +
        func.coalesce(reactions_sub.c.cnt, 0) * 2 +
        func.coalesce(comments_sub.c.cnt, 0) * 4
    )

    stmt = select(
        User,
        engagement_score_expr.label("engagement_score")
    ).outerjoin(
        views_sub, User.id == views_sub.c.user_id
    ).outerjoin(
        clicks_sub, User.id == clicks_sub.c.user_id
    ).outerjoin(
        saves_sub, User.id == saves_sub.c.user_id
    ).outerjoin(
        reactions_sub, User.id == reactions_sub.c.user_id
    ).outerjoin(
        comments_sub, User.id == comments_sub.c.user_id
    ).order_by(User.id.desc())

    if search:
        stmt = stmt.where(
            or_(User.name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
        )
    if role:
        if role.lower() == "admin":
            stmt = stmt.where(User.is_admin == True)
        elif role.lower() == "user":
            stmt = stmt.where(User.is_admin == False)
    return stmt


@bp.route("/rows", methods=["GET"])
def users_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    role   = request.args.get("role", "").strip()

    items, total, pages = _paginate_manual(search, role, page, per_page)

    users = []
    for u, score in items:
        u.engagement_score = score or 0
        users.append(u)

    html = render_template(
        "admin/control_panel/users/_rows.html",
        items=users,
    )
    return make_rows_response(
        html,
        total=total,
        pages=pages,
        page=page,
    )


@bp.route("/<int:id>/inspect", methods=["GET"])
def inspect_user(id):
    """Return server-rendered HTML for the user inspect modal body."""
    user = db.session.get(User, id)
    if not user:
        return "<p class='text-muted'>User not found.</p>", 404

    # 1. Activity Summary
    views_count = db.session.scalar(select(func.count(View.id)).where(View.user_id == id)) or 0
    clicks_count = db.session.scalar(select(func.count(ItemClick.id)).where(ItemClick.user_id == id)) or 0
    saves_count = db.session.scalar(select(func.count(Save.id)).where(Save.user_id == id)) or 0
    reactions_count = db.session.scalar(select(func.count(Reaction.id)).where(Reaction.user_id == id)) or 0
    comments_count = db.session.scalar(select(func.count(Comment.id)).where(Comment.user_id == id)) or 0

    # 2. Content Consumption (from UserEntityInterest)
    top_categories = db.session.execute(
        select(Category.name, func.sum(UserEntityInterest.score).label("total_score"))
        .join(UserEntityInterest, UserEntityInterest.category_id == Category.id)
        .join(UserInterest, UserInterest.id == UserEntityInterest.user_interest_id)
        .where(UserInterest.user_id == id)
        .group_by(Category.name)
        .order_by(func.sum(UserEntityInterest.score).desc())
        .limit(5)
    ).all()

    top_topics = db.session.execute(
        select(Topic.name, func.sum(UserEntityInterest.score).label("total_score"))
        .join(UserEntityInterest, UserEntityInterest.topic_id == Topic.id)
        .join(UserInterest, UserInterest.id == UserEntityInterest.user_interest_id)
        .where(UserInterest.user_id == id)
        .group_by(Topic.name)
        .order_by(func.sum(UserEntityInterest.score).desc())
        .limit(5)
    ).all()

    top_brands = db.session.execute(
        select(Brand.name, func.sum(UserEntityInterest.score).label("total_score"))
        .join(UserEntityInterest, UserEntityInterest.brand_id == Brand.id)
        .join(UserInterest, UserInterest.id == UserEntityInterest.user_interest_id)
        .where(UserInterest.user_id == id)
        .group_by(Brand.name)
        .order_by(func.sum(UserEntityInterest.score).desc())
        .limit(5)
    ).all()

    # 3. Recommendation Engagement
    recs_seen_rows = db.session.execute(
        select(RecommendationImpression.entity_ids).where(RecommendationImpression.user_id == id)
    ).scalars().all()
    recs_seen = sum(len(ids) if isinstance(ids, list) else 0 for ids in recs_seen_rows)

    recs_clicked = db.session.scalar(
        select(func.count(RecommendationClick.id)).where(RecommendationClick.user_id == id)
    ) or 0
    rec_ctr = (recs_clicked / recs_seen * 100) if recs_seen > 0 else 0.0

    # 4. Comments Sentiment Summary
    sentiment_counts = db.session.execute(
        select(Comment.sentiment, func.count(Comment.id))
        .where(Comment.user_id == id)
        .group_by(Comment.sentiment)
    ).all()

    sentiment_dict = {
        "positive": 0,
        "neutral": 0,
        "negative": 0
    }
    for sent, count in sentiment_counts:
        if sent:
            sent_lower = sent.lower()
            if sent_lower in sentiment_dict:
                sentiment_dict[sent_lower] += count
            else:
                sentiment_dict[sent_lower] = count

    recent_comments = db.session.execute(
        select(Comment)
        .where(Comment.user_id == id)
        .order_by(Comment.created_at.desc())
        .limit(5)
    ).scalars().all()

    # 5. Moderation Signals (Dummy since no DB tables exist)
    moderation_signals = {
        "warnings": 0,
        "reported_content": 0,
        "deleted_comments": 0
    }

    return render_template(
        "admin/control_panel/users/_inspect.html",
        user=user,
        activity={
            "views": views_count,
            "clicks": clicks_count,
            "saves": saves_count,
            "reactions": reactions_count,
            "comments": comments_count
        },
        content_consumption={
            "categories": top_categories,
            "topics": top_topics,
            "brands": top_brands
        },
        recommendation={
            "seen": recs_seen,
            "clicked": recs_clicked,
            "ctr": rec_ctr
        },
        comments_summary={
            "total": comments_count,
            "sentiment": sentiment_dict,
            "recent": recent_comments
        },
        moderation=moderation_signals
    )


@bp.route("/<int:id>/toggle-admin", methods=["POST"])
def toggle_admin(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.is_admin = not user.is_admin
    db.session.commit()
    return jsonify({"success": True, "is_admin": user.is_admin})
