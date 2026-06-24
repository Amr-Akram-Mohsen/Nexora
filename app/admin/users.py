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
from sqlalchemy import select, or_, and_, func
from app.domains.taxonomy.models import Category, Topic, Brand
from app.domains.interaction.models import Comment, Reaction, View, Save, Share, ItemClick, RecommendationImpression, RecommendationClick
from app.domains.recommendation.models import UserInterest, UserEntityInterest

bp = Blueprint("api_user", __name__, url_prefix="/admin/users")
@bp.route("/stats", methods=["GET"])
def users_stats():
    """Return JSON metrics for the users dashboard charts."""
    role_dist = db.session.execute(select(User.is_admin, func.count(User.id)).group_by(User.is_admin)).all()
    roles = {"Admins": sum(c for is_admin, c in role_dist if is_admin), "Users": sum(c for is_admin, c in role_dist if not is_admin)}

    provider_dist = db.session.execute(select(User.provider, func.count(User.id)).group_by(User.provider)).all()
    providers = {p or "local": c for p, c in provider_dist}

    # SQLite compatible date grouping (truncate to month)
    from sqlalchemy.dialects.sqlite import DATE
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    # Let's get the last 6 months of growth
    # Use to_char since the environment is using PostgreSQL
    growth_data = db.session.execute(
        select(func.to_char(User.created_at, 'YYYY-MM').label('month'), func.count(User.id))
        .group_by('month')
        .order_by('month')
        .limit(12)
    ).all()
    
    growth = {m: c for m, c in growth_data if m}

    return jsonify({
        "roles": roles,
        "providers": providers,
        "growth": growth
    })


@bp.before_request
@admin_required
def require_admin():
    """Ensure all user management endpoints require admin privilege."""
    pass


def _paginate_manual(search, role, status, verified, subscription, provider, sort_by, sort_dir, page, per_page):
    stmt, count_stmt = _build_user_query(search, role, status, verified, subscription, provider, sort_by, sort_dir)
            
    total = db.session.scalar(count_stmt) or 0
    
    # Calculate summary stats based on current query
    from app.domains.user.models import NewsletterSubscriber
    stats = {
        "active": db.session.scalar(count_stmt.where(User.is_active == True)) or 0,
        "admins": db.session.scalar(count_stmt.where(User.is_admin == True)) or 0,
        "verified": db.session.scalar(count_stmt.where(User.is_verified == True)) or 0,
        "subscribed": db.session.scalar(
            count_stmt.outerjoin(NewsletterSubscriber, User.id == NewsletterSubscriber.user_id)
            .where(NewsletterSubscriber.is_confirmed == True, NewsletterSubscriber.unsubscribed_at.is_(None))
        ) or 0
    }
    
    # items query
    offset = (page - 1) * per_page
    items_stmt = stmt.limit(per_page).offset(offset)
    items = db.session.execute(items_stmt).all() # returns list of Rows: (User, score)
    
    import math
    pages = math.ceil(total / per_page) if per_page else 1
    return items, total, pages, stats


@bp.route("/", methods=["GET"])
def list_users():
    """Paginated user listing with optional search and role filter."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    role   = request.args.get("user_role_filter", "").strip()
    status = request.args.get("user_status_filter", "").strip()
    verified = request.args.get("user_verified_filter", "").strip()
    subscription = request.args.get("user_subscription_filter", "").strip()
    provider = request.args.get("user_provider_filter", "").strip()
    sort_by = request.args.get("sort_by", "").strip()
    sort_dir = request.args.get("sort_dir", "desc").strip()

    items, total, pages, stats = _paginate_manual(search, role, status, verified, subscription, provider, sort_by, sort_dir, page, per_page)

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
    'comments': 4,
    'shares': 3
}

def _build_user_query(search, role, status, verified, subscription, provider, sort_by=None, sort_dir=None):
    """Shared query builder for users listing and rows endpoint."""
    views_sub = select(View.user_id, func.count(View.id).label("cnt")).where(View.user_id.isnot(None)).group_by(View.user_id).subquery()
    clicks_sub = select(ItemClick.user_id, func.count(ItemClick.id).label("cnt")).where(ItemClick.user_id.isnot(None)).group_by(ItemClick.user_id).subquery()
    saves_sub = select(Save.user_id, func.count(Save.id).label("cnt")).group_by(Save.user_id).subquery()
    reactions_sub = select(Reaction.user_id, func.count(Reaction.id).label("cnt")).group_by(Reaction.user_id).subquery()
    comments_sub = select(Comment.user_id, func.count(Comment.id).label("cnt")).group_by(Comment.user_id).subquery()
    shares_sub = select(Share.user_id, func.count(Share.id).label("cnt")).group_by(Share.user_id).subquery()

    engagement_score_expr = (
        func.coalesce(views_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['views'] +
        func.coalesce(clicks_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['clicks'] +
        func.coalesce(saves_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['saves'] +
        func.coalesce(reactions_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['reactions'] +
        func.coalesce(comments_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['comments'] +
        func.coalesce(shares_sub.c.cnt, 0) * ENGAGEMENT_WEIGHTS['shares']
    )

    from app.domains.user.models import NewsletterSubscriber

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
    ).outerjoin(
        shares_sub, User.id == shares_sub.c.user_id
    )

    if sort_by == 'engagement_score':
        stmt = stmt.order_by(engagement_score_expr.desc() if sort_dir == 'desc' else engagement_score_expr.asc())
    elif sort_by == 'joined':
        stmt = stmt.order_by(User.created_at.desc() if sort_dir == 'desc' else User.created_at.asc())
    elif sort_by == 'last_active':
        stmt = stmt.order_by(User.last_login_at.desc() if sort_dir == 'desc' else User.last_login_at.asc())
    else:
        stmt = stmt.order_by(User.id.desc())

    count_stmt = select(func.count(User.id))

    if search:
        search_filter = or_(User.name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)
    if role:
        role_filter = User.is_admin == True if role.lower() == "admin" else User.is_admin == False
        stmt = stmt.where(role_filter)
        count_stmt = count_stmt.where(role_filter)
    if status:
        status_filter = User.is_active == True if status.lower() == "active" else User.is_active == False
        stmt = stmt.where(status_filter)
        count_stmt = count_stmt.where(status_filter)
    if verified:
        verified_filter = User.is_verified == True if verified.lower() == "true" else User.is_verified == False
        stmt = stmt.where(verified_filter)
        count_stmt = count_stmt.where(verified_filter)
    if provider:
        provider_filter = User.provider == 'google' if provider.lower() == "google" else (User.provider.is_(None) | (User.provider == 'local'))
        stmt = stmt.where(provider_filter)
        count_stmt = count_stmt.where(provider_filter)
    if subscription:
        if subscription.lower() == "subscribed":
            sub_filter = User.newsletter_subscription.has(and_(NewsletterSubscriber.is_confirmed == True, NewsletterSubscriber.unsubscribed_at.is_(None)))
        else:
            sub_filter = ~User.newsletter_subscription.has(and_(NewsletterSubscriber.is_confirmed == True, NewsletterSubscriber.unsubscribed_at.is_(None)))
        stmt = stmt.where(sub_filter)
        count_stmt = count_stmt.where(sub_filter)
        
    return stmt, count_stmt


@bp.route("/rows", methods=["GET"])
def users_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    role   = request.args.get("user_role_filter", "").strip()
    status = request.args.get("user_status_filter", "").strip()
    verified = request.args.get("user_verified_filter", "").strip()
    subscription = request.args.get("user_subscription_filter", "").strip()
    provider = request.args.get("user_provider_filter", "").strip()
    sort_by = request.args.get("sort_by", "").strip()
    sort_dir = request.args.get("sort_dir", "desc").strip()

    items, total, pages, stats = _paginate_manual(search, role, status, verified, subscription, provider, sort_by, sort_dir, page, per_page)

    users = []
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for u, score in items:
        recency_days = (now - u.last_login_at).days if u.last_login_at else None
        users.append({
            "id": u.id,
            "name": f"{u.name}\n{u.email}",
            "is_verified": u.is_verified,
            "role": 'admin' if u.is_admin else 'user',
            "subscription": 'subscribed' if u.newsletter_subscription and u.newsletter_subscription.is_active else 'not subscribed',
            "status": 'active' if u.is_active else 'inactive',
            "joined": u.created_at.strftime('%Y-%m-%d') if u.created_at else "—",
            "last-active": u.last_login_at.strftime('%Y-%m-%d %H:%M') if u.last_login_at else "Never",
            "recency_days": recency_days,
            "engagement-score": round(score, 1) if score else 0,
            "engagement-tier": "Power User" if score and score >= 200 else ("High" if score and score >= 50 else ("Medium" if score and score >= 10 else "Low"))
        })

    html = render_template(
        "admin/components/_rows.html",
        items=users,
        domain_type="user"
    )
    resp = make_rows_response(
        html,
        total=total,
        pages=pages,
        page=page,
    )
    resp.headers["X-Active-Count"] = stats["active"]
    resp.headers["X-Admin-Count"] = stats["admins"]
    resp.headers["X-Verified-Count"] = stats["verified"]
    resp.headers["X-Subscribed-Count"] = stats["subscribed"]
    return resp


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
    
    recs_clicked = db.session.scalar(select(func.count(RecommendationClick.id)).where(RecommendationClick.user_id == id))

    engagement_score = (views_count * ENGAGEMENT_WEIGHTS['views']) + (clicks_count * ENGAGEMENT_WEIGHTS['clicks']) + (saves_count * ENGAGEMENT_WEIGHTS['saves']) + (reactions_count * ENGAGEMENT_WEIGHTS['reactions']) + (comments_count * ENGAGEMENT_WEIGHTS['comments']) + (shares_count * ENGAGEMENT_WEIGHTS['shares'])

    from app.admin.helpers import format_date, format_datetime
    from app.admin.tables import get_inspect_table
    
    provider = user.provider.title() if user.provider else "Local"
    verified_str = "Yes" if user.is_verified else "No"
    
    brand_ids = set()
    category_ids = set()
    topic_ids = set()
    for ui in user.user_interests:
        for score in ui.entity_scores:
            if score.brand_id: brand_ids.add(score.brand_id)
            if score.category_id: category_ids.add(score.category_id)
            if score.topic_id: topic_ids.add(score.topic_id)
            
    brands_map = {b.id: b.name for b in db.session.execute(select(Brand).where(Brand.id.in_(brand_ids))).scalars()} if brand_ids else {}
    categories_map = {c.id: c.name for c in db.session.execute(select(Category).where(Category.id.in_(category_ids))).scalars()} if category_ids else {}
    topics_map = {t.id: t.name for t in db.session.execute(select(Topic).where(Topic.id.in_(topic_ids))).scalars()} if topic_ids else {}

    item_ids = {ui.target_id for ui in user.user_interests if ui.target_type == 'item'}
    article_ids = {ui.target_id for ui in user.user_interests if ui.target_type in ('article', 'content')}
    items_map = {}
    articles_map = {}
    if item_ids:
        from app.domains.item.models import Item
        items_map = {i.id: i.name for i in db.session.execute(select(Item).where(Item.id.in_(item_ids))).scalars()}
    if article_ids:
        from app.domains.content.models import Content
        articles_map = {c.id: c.title for c in db.session.execute(select(Content).where(Content.id.in_(article_ids))).scalars()}

    interests_data = []
    agg_brands = {}
    agg_categories = {}
    agg_topics = {}

    for ui in user.user_interests:
        target_name = f"{ui.target_type.title()} #{ui.target_id}"
        if ui.target_type == 'item' and ui.target_id in items_map:
            target_name = items_map[ui.target_id]
        elif ui.target_type in ('article', 'content') and ui.target_id in articles_map:
            target_name = articles_map[ui.target_id]
        
        item_score = 0
        for s in ui.entity_scores:
            item_score += s.score
            if s.brand_id and s.brand_id in brands_map:
                agg_brands[brands_map[s.brand_id]] = agg_brands.get(brands_map[s.brand_id], 0) + s.score
            if s.category_id and s.category_id in categories_map:
                agg_categories[categories_map[s.category_id]] = agg_categories.get(categories_map[s.category_id], 0) + s.score
            if s.topic_id and s.topic_id in topics_map:
                agg_topics[topics_map[s.topic_id]] = agg_topics.get(topics_map[s.topic_id], 0) + s.score
        
        interests_data.append({
            "target_name": target_name,
            "target_type": ui.target_type,
            "interaction_count": ui.interaction_count,
            "last_interaction": format_date(ui.last_interaction_at),
            "score": round(item_score, 1)
        })
    
    interests_data.sort(key=lambda x: x["last_interaction"], reverse=True)

    def sort_agg(d):
        return [{"name": k, "score": round(v, 1)} for k, v in sorted(d.items(), key=lambda item: item[1], reverse=True)[:5]]

    aggregated_affinities = {
        "Brands": sort_agg(agg_brands),
        "Categories": sort_agg(agg_categories),
        "Topics": sort_agg(agg_topics)
    }

    user_interests_data = None
    if interests_data or agg_brands:
        user_interests_data = {
            "items": interests_data,
            "affinities": aggregated_affinities
        }

    engagement_breakdown_data = {
        "Views": views_count,
        "Item Clicks": clicks_count,
        "Saves": saves_count,
        "Reactions": reactions_count,
        "Comments": comments_count,
        "Shares": shares_count,
        "Recs Clicked": recs_clicked
    }

    import urllib.parse
    user_email_enc = urllib.parse.quote(user.email) if user.email else ""

    reactions_breakdown = db.session.execute(
        select(Reaction.type, func.count(Reaction.id))
        .where(Reaction.user_id == id)
        .group_by(Reaction.type)
    ).all()
    likes = sum(c for t, c in reactions_breakdown if t == 'like')
    dislikes = sum(c for t, c in reactions_breakdown if t == 'dislike')
    reactions_str = f"{reactions_count} (👍 {likes}, 👎 {dislikes})"

    sentiments = db.session.execute(
        select(Comment.sentiment, func.count(Comment.id))
        .where(Comment.user_id == id)
        .group_by(Comment.sentiment)
    ).all()
    pos = sum(c for s, c in sentiments if s == 'positive')
    neu = sum(c for s, c in sentiments if s == 'neutral')
    neg = sum(c for s, c in sentiments if s == 'negative')
    spam = sum(c for s, c in sentiments if s == 'spam')
    comments_str = f"{comments_count} (Pos: {pos}, Neu: {neu}, Neg: {neg}, Spam: {spam})"

    reactions_link = {"value": reactions_str, "link": f'/admin/moderation?reactions_user={user_email_enc}'} if reactions_count > 0 else {"value": "0"}
    comments_link = {"value": comments_str, "link": f'/admin/moderation?comments_user={user_email_enc}'} if comments_count > 0 else {"value": "0"}
    shares_link = {"value": str(shares_count), "link": f'/admin/moderation?shares_user={user_email_enc}'} if shares_count > 0 else {"value": "0"}
    saves_link = {"value": str(saves_count), "link": f'/admin/moderation?saves_user={user_email_enc}'} if saves_count > 0 else {"value": "0"}
    clicks_link = str(clicks_count) # Clicks are aggregated by target, so no direct user filter yet

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
    latest_view = db.session.scalar(select(View).where(View.user_id == id).order_by(View.created_at.desc()).limit(1))
    latest_reaction = db.session.scalar(select(Reaction).where(Reaction.user_id == id).order_by(Reaction.created_at.desc()).limit(1))
    latest_share = db.session.scalar(select(Share).where(Share.user_id == id).order_by(Share.created_at.desc()).limit(1))
    latest_click = db.session.scalar(select(ItemClick).where(ItemClick.user_id == id).order_by(ItemClick.created_at.desc()).limit(1))

    activities = []
    if latest_comment: activities.append((latest_comment.created_at, f"Commented: {latest_comment.content[:50]}..."))
    if latest_save and latest_save.target:
        title = latest_save.target.title if latest_save.target_type == 'content' else latest_save.target.name
        activities.append((latest_save.created_at, f"Saved: {title}"))
    if latest_view and latest_view.target:
        title = latest_view.target.title if latest_view.target_type == 'content' else latest_view.target.name
        activities.append((latest_view.created_at, f"Viewed: {title}"))
    if latest_reaction and latest_reaction.target:
        title = latest_reaction.target.title if latest_reaction.target_type == 'content' else (latest_reaction.target.name if hasattr(latest_reaction.target, 'name') else 'Comment')
        activities.append((latest_reaction.created_at, f"Reacted ({latest_reaction.type}): {title}"))
    if latest_share and latest_share.target:
        title = latest_share.target.title if latest_share.target_type == 'content' else latest_share.target.name
        activities.append((latest_share.created_at, f"Shared: {title}"))
    if latest_click:
        activities.append((latest_click.created_at, f"Clicked Item Link"))

    if activities:
        activities.sort(key=lambda x: x[0], reverse=True)
        recent_activity = activities[0][1]

    engagement_tier = "Power User" if engagement_score >= 200 else ("High" if engagement_score >= 50 else ("Medium" if engagement_score >= 10 else "Low"))

    subscription_status = "Not Subscribed"
    if user.newsletter_subscription:
        sub_status_text = "Active" if user.newsletter_subscription.is_active else ("Unsubscribed" if user.newsletter_subscription.unsubscribed_at else "Unconfirmed")
        sub_created = format_date(user.newsletter_subscription.created_at, fmt='%b %d, %Y') if user.newsletter_subscription.created_at else "—"
        sub_unsubbed = format_date(user.newsletter_subscription.unsubscribed_at, fmt='%b %d, %Y') if user.newsletter_subscription.unsubscribed_at else ""
        subscription_status = f"{sub_status_text} (Joined: {sub_created})"
        if sub_unsubbed:
            subscription_status += f" [Unsubbed: {sub_unsubbed}]"

    data = {
        "id": f"#{user.id}",
        "name": user.name or "—",
        "email": user.email,
        "role": "Admin" if user.is_admin else "User",
        "subscription": subscription_status,
        "status": "Active" if user.is_active else "Inactive",
        "joined": format_date(user.created_at, fmt='%b %d, %Y') if user.created_at else "—",
        "last active": format_datetime(user.last_login_at, fmt='%b %d, %Y %H:%M') if user.last_login_at else "Never",
        
        "provider": provider,
        "verified": verified_str,
        "verified at": format_datetime(user.verified_at, fmt='%b %d, %Y %H:%M') if user.verified_at else "—",
        "verification sent": format_datetime(user.verification_sent_at, fmt='%b %d, %Y %H:%M') if user.verification_sent_at else "—",
        "password changed": format_datetime(user.password_changed_at, fmt='%b %d, %Y %H:%M') if user.password_changed_at else "—",

        "engagement tier": {"value": engagement_tier, "badge": True, "badge_class": "bg-primary"},
        "engagement profile": {"value": engagement_profile, "badge": True, "badge_class": "bg-secondary"},
        "engagement score": str(engagement_score),
        "views": str(views_count),
        "reactions": reactions_link,
        "comments": comments_link,
        "saves": saves_link,
        "shares": shares_link,
        "item clicks": clicks_link,
        "recommendations shown": str(recs_seen),
        "recommendations clicked": str(recs_clicked),
        
        "recent activity": recent_activity
    }
    inspect_table = get_inspect_table("users", data)

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    recency = None
    if user.last_login_at:
        days_ago = (now - user.last_login_at).days
        if days_ago <= 1:
            recency = {"value": "Active Today", "badge_class": "badge-health-high"}
        elif days_ago <= 7:
            recency = {"value": "Active this Week", "badge_class": "badge-health-medium"}
        else:
            recency = {"value": "Inactive", "badge_class": "badge-health-low"}

    inspect_header = {"badges": [recency] if recency else []}

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
        "engagement_breakdown": engagement_breakdown_data,
        "user_interests": user_interests_data,
        "actions": actions,
        "inspect_id": user.id,
        "inspect_header": inspect_header,
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
