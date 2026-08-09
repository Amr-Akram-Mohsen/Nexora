from flask import Blueprint, jsonify
from app.web.routes.admin.helpers import apply_admin_guard
from app.core.extensions import db
from app.domains.user.models import User
from app.domains.interaction.models import RecommendationImpression, RecommendationClick
from sqlalchemy import select, func, text

bp = Blueprint("api_analytics", __name__, url_prefix="/admin/analytics")

apply_admin_guard(bp)

@bp.route("/stats", methods=["GET"])
def get_analytics_stats():
    from app.domains.user.service.admin.admin import get_admin_audience_analytics_stats
    return jsonify(get_admin_audience_analytics_stats())
