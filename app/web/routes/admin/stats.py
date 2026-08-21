"""
Admin dashboard statistics and top-list endpoints.
"""
from flask import Blueprint, jsonify
from app.web.routes.admin.helpers import apply_admin_guard
from app.domains.analytics.service.admin import (
    get_admin_dashboard_stats_data,
    get_admin_top_contents,
    get_admin_top_items,
)

bp = Blueprint("api_dashboard", __name__, url_prefix="/admin/dashboard")
apply_admin_guard(bp)


@bp.route("/stats", methods=["GET"])
def dashboard_stats():
    """Enhanced dashboard metrics, aggregates, distributions, and trends."""
    return jsonify(get_admin_dashboard_stats_data())


@bp.route("/top-contents", methods=["GET"])
def top_contents():
    """Top 5 content products by view count for the overview panel."""
    return jsonify(get_admin_top_contents())


@bp.route("/top-products", methods=["GET"])
def top_items():
    """Top 5 products by click count for the overview panel."""
    return jsonify(get_admin_top_items())
