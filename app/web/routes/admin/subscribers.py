from flask import Blueprint, jsonify, request, render_template
from app.domains.user.models import NewsletterSubscriber, User
from app.core.decorators import admin_required
from app.core.extensions import db
from app.web.routes.admin.helpers import parse_pagination_params
from sqlalchemy import select, or_, and_, func

bp = Blueprint("api_subscribers", __name__, url_prefix="/admin/subscribers")

@bp.before_request
@admin_required
def require_admin():
    pass

def _build_subscriber_query(search, status, has_user):
    stmt = select(NewsletterSubscriber).outerjoin(User, NewsletterSubscriber.user_id == User.id).order_by(NewsletterSubscriber.id.desc())
    count_stmt = select(func.count(NewsletterSubscriber.id))

    if search:
        search_filter = or_(NewsletterSubscriber.email.ilike(f"%{search}%"), User.name.ilike(f"%{search}%"))
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)
    
    if status:
        if status == 'confirmed':
            status_filter = and_(NewsletterSubscriber.is_confirmed == True, NewsletterSubscriber.unsubscribed_at.is_(None))
        elif status == 'unconfirmed':
            status_filter = NewsletterSubscriber.is_confirmed == False
        elif status == 'unsubscribed':
            status_filter = NewsletterSubscriber.unsubscribed_at.isnot(None)
        stmt = stmt.where(status_filter)
        count_stmt = count_stmt.where(status_filter)
        
    if has_user:
        user_filter = NewsletterSubscriber.user_id.isnot(None) if has_user == 'true' else NewsletterSubscriber.user_id.is_(None)
        stmt = stmt.where(user_filter)
        count_stmt = count_stmt.where(user_filter)

    return stmt, count_stmt

@bp.route("/rows", methods=["GET"])
def subscribers_rows():
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    status = request.args.get("subscriber_status_filter", "").strip()
    has_user = request.args.get("subscriber_user_filter", "").strip()

    stmt, count_stmt = _build_subscriber_query(search, status, has_user)
    
    total = db.session.scalar(count_stmt) or 0
    
    # Calculate stats
    stats = {
        "total": total,
        "confirmed": db.session.scalar(count_stmt.where(and_(NewsletterSubscriber.is_confirmed == True, NewsletterSubscriber.unsubscribed_at.is_(None)))) or 0,
        "unconfirmed": db.session.scalar(count_stmt.where(NewsletterSubscriber.is_confirmed == False)) or 0,
        "unsubscribed": db.session.scalar(count_stmt.where(NewsletterSubscriber.unsubscribed_at.isnot(None))) or 0,
        "anonymous": db.session.scalar(count_stmt.where(NewsletterSubscriber.user_id.is_(None))) or 0
    }

    offset = (page - 1) * per_page
    items = db.session.scalars(stmt.limit(per_page).offset(offset)).all()
    
    import math
    pages = math.ceil(total / per_page) if per_page else 1

    subscribers = []
    for s in items:
        status_label = 'active' if (s.is_confirmed and not s.unsubscribed_at) else ('inactive' if s.unsubscribed_at else 'pending')
        subscribers.append({
            "id": s.id,
            "email": s.email,
            "status": status_label,
            "user_link": s.user_id,
            "subscribed_at": s.created_at.strftime('%Y-%m-%d') if s.created_at else "—",
            "unsubscribed_at": s.unsubscribed_at.strftime('%Y-%m-%d') if s.unsubscribed_at else "—"
        })

    html = render_template("admin/components/_rows.html", items=subscribers, domain="subscribers")
    
    res = db.make_response(html)
    res.headers["X-Total"] = total
    res.headers["X-Pages"] = pages
    res.headers["X-Confirmed"] = stats["confirmed"]
    res.headers["X-Unconfirmed"] = stats["unconfirmed"]
    res.headers["X-Unsubscribed"] = stats["unsubscribed"]
    res.headers["X-Anonymous"] = stats["anonymous"]
    return res

@bp.route("/<int:id>", methods=["DELETE"])
def delete_subscriber(id):
    sub = db.session.get(NewsletterSubscriber, id)
    if not sub:
        return jsonify({"error": "Subscriber not found"}), 404
    db.session.delete(sub)
    db.session.commit()
    return jsonify({"success": True})
