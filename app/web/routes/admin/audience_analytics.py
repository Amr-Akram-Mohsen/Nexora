from flask import Blueprint, jsonify, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.user.models import User
from app.domains.interaction.models import RecommendationImpression, RecommendationClick
from sqlalchemy import select, func, text

bp = Blueprint("api_audience_analytics", __name__, url_prefix="/admin/audience-analytics")

@bp.before_request
@admin_required
def require_admin():
    pass

@bp.route("/stats", methods=["GET"])
def get_analytics_stats():
    from app.domains.user.service.admin import get_admin_audience_analytics_stats
    return jsonify(get_admin_audience_analytics_stats())
