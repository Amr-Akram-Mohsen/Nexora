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


ENGAGEMENT_WEIGHTS = {
    'views': 1,
    'clicks': 2,
    'saves': 3,
    'reactions': 2,
    'comments': 4
}

def _build_user_query(search, role):
    """Shared query builder for users listing and rows endpoint."""
    views_sub = select(View.user_id, func.count(View.id).label("cnt")).where(View.user_id.isnot(None)).group_by(View.user_id).subquery()
    clicks_sub = select(ItemClick.user_id, func.count(ItemClick.id).label("cnt")).where(ItemClick.user_id.isnot(None)).group_by(ItemClick.user_id).subquery()
    saves_sub = select(Save.user_id, func.count(Save.id).label("cnt")).group_by(Save.user_id).subquery()
    reactions_sub = select(Reaction.user_id, func.count(Reaction.id).label("cnt")).group_by(Reaction.user_id).subquery()
    comments_sub = select(Comment.user_id, func.count(Comment.id).label("cnt")).group_by(Comment.user_id).subquery()

    engagement_score_expr = (
        func.coalesce(views_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['views'] +
        func.coalesce(clicks_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['clicks'] +
        func.coalesce(saves_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['saves'] +
        func.coalesce(reactions_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['reactions'] +
        func.coalesce(comments_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['comments']
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
        users.append({
            "id": u.id,
            "name": f'''{u.name}
            {u.email}'''
            ,
            "role": 'admin' if u.is_admin else 'user',
            "subscription": 'subscribed' if u.newsletter_subscription and u.newsletter_subscription.is_active else 'not subscribed',
            "status": 'active' if u.is_active else 'inactive',
            "joined": u.created_at.strftime('%Y-%m-%d') if u.created_at else "—",
            "last-active": u.last_login_at.strftime('%Y-%m-%d %H:%M') if u.last_login_at else "Never",
            "engagement-score": round(score, 1) if score else 0,
        })

    html = render_template(
        "admin/components/_rows.html",
        items=users,
        domain_type="user"
    )
    return make_rows_response(
        html,
        total=total,
        pages=pages,
        page=page,
    )


def build_user_inspect_data(id):
    """Return dictionary of data needed for the user inspect/detail view."""
    from sqlalchemy.orm import selectinload
    stmt_user = select(User).options(
        selectinload(User.user_interests).selectinload(UserInterest.entity_scores),
        selectinload(User.newsletter_subscription)
    ).where(User.id == id)
    user = db.session.scalar(stmt_user)
    
    if not user:
        return None

    stmt_metrics = select(
        (select(func.count(View.id)).where(View.user_id == id)).scalar_subquery(),
        (select(func.count(ItemClick.id)).where(ItemClick.user_id == id)).scalar_subquery(),
        (select(func.count(Save.id)).where(Save.user_id == id)).scalar_subquery(),
        (select(func.count(Reaction.id)).where(Reaction.user_id == id)).scalar_subquery(),
        (select(func.count(Comment.id)).where(Comment.user_id == id)).scalar_subquery(),
        (select(func.count(Share.id)).where(Share.user_id == id)).scalar_subquery()
    )
    views_count, clicks_count, saves_count, reactions_count, comments_count, shares_count = db.session.execute(stmt_metrics).first()

    recs_seen_rows = db.session.execute(
        select(RecommendationImpression.entity_ids).where(RecommendationImpression.user_id == id)
    ).scalars().all()
    recs_seen = sum(len(ids) if isinstance(ids, list) else 0 for ids in recs_seen_rows)

    engagement_score = (views_count * ENGAGEMENT_WEIGHTS['views']) + (clicks_count * ENGAGEMENT_WEIGHTS['clicks']) + (saves_count * ENGAGEMENT_WEIGHTS['saves']) + (reactions_count * ENGAGEMENT_WEIGHTS['reactions']) + (comments_count * ENGAGEMENT_WEIGHTS['comments'])

    from app.admin.helpers import format_date, format_datetime
    from app.admin.tables import get_inspect_table
    
    provider = user.provider.title() if user.provider else "Local"
    verified_str = "Yes" if user.is_verified else "No"
    
    interests_html = ""
    for ui in user.user_interests:
        target_name = getattr(ui.target, 'name', getattr(ui.target, 'title', f"{ui.target_type} #{ui.target_id}")) if ui.target else f"{ui.target_type} #{ui.target_id}"
        interests_html += f"<div class='mb-2'><b>{target_name}</b> ({ui.interaction_count} interactions)</div>"
        for score in ui.entity_scores:
            entity = ""
            if score.brand_id:
                brand = db.session.get(Brand, score.brand_id)
                entity = f"Brand: {brand.name}" if brand else "Brand"
            elif score.category_id:
                category = db.session.get(Category, score.category_id)
                entity = f"Category: {category.name}" if category else "Category"
            elif score.topic_id:
                topic = db.session.get(Topic, score.topic_id)
                entity = f"Topic: {topic.name}" if topic else "Topic"
            if entity:
                interests_html += f"<div class='ml-4 text-xs text-muted'>- {entity}: {score.score} pts</div>"
    
    if not interests_html:
        interests_html = "—"

    counts_dict = {
        "Commenter": comments_count,
        "Saver": saves_count,
        "Sharer": shares_count,
        "Clicker": clicks_count,
        "Viewer": views_count
    }
    max_count = max(counts_dict.values()) if any(counts_dict.values()) else 0
    engagement_profile = "Inactive"
    if max_count > 0:
        for profile, count in counts_dict.items():
            if count == max_count:
                engagement_profile = profile
                break

    recent_activity = "—"
    latest_comment = db.session.scalar(select(Comment).where(Comment.user_id == id).order_by(Comment.created_at.desc()).limit(1))
    latest_save = db.session.scalar(select(Save).where(Save.user_id == id).order_by(Save.created_at.desc()).limit(1))
    
    if latest_comment and latest_save:
        if latest_comment.created_at > latest_save.created_at:
            recent_activity = f"<b>Commented:</b> {latest_comment.content[:50]}..."
        else:
            title = latest_save.target.title if latest_save.target_type == 'content' else latest_save.target.name
            recent_activity = f"<b>Saved:</b> {title}"
    elif latest_comment:
        recent_activity = f"<b>Commented:</b> {latest_comment.content[:50]}..."
    elif latest_save:
        title = latest_save.target.title if latest_save.target_type == 'content' else latest_save.target.name
        recent_activity = f"<b>Saved:</b> {title}"

    data = {
        "id": f"#{user.id}",
        "name": user.name or "—",
        "email": user.email,
        "role": "Admin" if user.is_admin else "User",
        "subscription": "Subscribed" if user.newsletter_subscription and user.newsletter_subscription.is_active else "Not Subscribed",
        "status": "Active" if user.is_active else "Inactive",
        "joined": format_date(user.created_at, fmt='%b %d, %Y') if user.created_at else "—",
        "last active": format_datetime(user.last_login_at, fmt='%b %d, %Y %H:%M') if user.last_login_at else "Never",
        
        "provider": provider,
        "verified": verified_str,
        "verified at": format_datetime(user.verified_at, fmt='%b %d, %Y %H:%M') if user.verified_at else "—",
        "password changed": format_datetime(user.password_changed_at, fmt='%b %d, %Y %H:%M') if user.password_changed_at else "—",

        "engagement profile": f"<span class='badge bg-primary'>{engagement_profile}</span>",
        "engagement score": str(engagement_score),
        "views": str(views_count),
        "reactions": str(reactions_count),
        "comments": str(comments_count),
        "saves": str(saves_count),
        "shares": str(shares_count),
        "item clicks": str(clicks_count),
        "recommendations shown": str(recs_seen),
        
        "interests": {"value": interests_html, "is_custom": True} if interests_html != "—" else "—",
        "recent activity": {"value": recent_activity, "is_custom": True} if recent_activity != "—" else "—"
    }
    inspect_table = get_inspect_table("users", data)

    actions = [
        {
            "label": "Demote to User" if user.is_admin else "Promote to Admin",
            "action_type": "toggle-admin",
            "extra_class": "user-action-toggle-admin",
            "attrs": {"data-action": "toggle-admin", "data-id": user.id, "data-name": (user.name or user.email)}
        },
        {
            "label": "Deactivate Account" if user.is_active else "Activate Account",
            "action_type": "toggle-active",
            "extra_class": "user-action-toggle-active",
            "attrs": {"data-action": "toggle-active", "data-id": user.id, "data-is-active": str(user.is_active).lower(), "data-name": (user.name or user.email)}
        },
        {
            "label": "Debug Personalization",
            "action_type": "view",
            "icon": "🧠",
            "extra_class": "inspect-action-debug-recs",
            "attrs": {"data-action": "inspect", "data-domain": "recommendations/user_interests", "data-id": user.id}
        },
        {
            "label": "Delete User",
            "action_type": "delete",
            "icon": "🗑",
            "extra_class": "user-action-delete",
            "attrs": {"data-action": "delete-user", "data-id": user.id, "data-name": (user.name or user.email)}
        }
    ]

    return {
        "inspect_table": inspect_table,
        "actions": actions,
        "inspect_id": user.id,
        "user_name": user.name or user.email
    }


@bp.route("/<int:id>/toggle-admin", methods=["POST"])
def toggle_admin(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.is_admin = not user.is_admin
    db.session.commit()
    return jsonify({"success": True, "is_admin": user.is_admin})
