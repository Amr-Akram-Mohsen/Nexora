"""
Admin audience analytics endpoints.
"""
from flask import Blueprint, jsonify
from app.web.routes.admin.helpers import apply_admin_guard
from app.domains.user.service.admin.admin import get_admin_audience_analytics_stats

bp = Blueprint("api_analytics", __name__, url_prefix="/admin/analytics")
apply_admin_guard(bp)


@bp.route("/stats", methods=["GET"])
def get_analytics_stats():
    return jsonify(get_admin_audience_analytics_stats())

