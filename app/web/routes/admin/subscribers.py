from flask import Blueprint, jsonify, request, render_template, make_response
from app.core.decorators import admin_required
from app.web.routes.admin.helpers import parse_pagination_params
from app.domains.user.service.admin import get_admin_subscribers_paginated
from app.application.user.admin import delete_subscriber_workflow

bp = Blueprint("api_subscribers", __name__, url_prefix="/admin/subscribers")

@bp.before_request
@admin_required
def require_admin():
    pass

@bp.route("/rows", methods=["GET"])
def subscribers_rows():
    page, per_page = parse_pagination_params(default_per_page=25)
    search = request.args.get("search", "").strip()
    status = request.args.get("subscriber_status_filter", "").strip()
    has_user = request.args.get("subscriber_user_filter", "").strip()

    items, total, pages, stats = get_admin_subscribers_paginated(search, status, has_user, page, per_page)

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
    
    res = make_response(html)
    res.headers["X-Total"] = total
    res.headers["X-Pages"] = pages
    res.headers["X-Confirmed"] = stats["confirmed"]
    res.headers["X-Unconfirmed"] = stats["unconfirmed"]
    res.headers["X-Unsubscribed"] = stats["unsubscribed"]
    res.headers["X-Anonymous"] = stats["anonymous"]
    return res

@bp.route("/<int:id>", methods=["DELETE"])
def delete_subscriber(id):
    success = delete_subscriber_workflow(id)
    if not success:
        return jsonify({"error": "Subscriber not found"}), 404
    return jsonify({"success": True})
