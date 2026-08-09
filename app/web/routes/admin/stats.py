# app/admin/stats.py
"""
Admin dashboard statistics and top-list endpoints.

Performance optimisations applied:
- Provider activity: N+1 loop (4 queries × N sources) replaced with 2
  aggregate queries joined in Python (R-02).
- Inactive content count derived arithmetically from total − active (R-16).
- 7-day growth trend uses a single GROUP BY query instead of a per-day loop (R-17).
- Interaction breakdown reads from the 60-second cached get_interactions_breakdown() (R-03).
- All queries use SQLAlchemy 2.0-style select() (R-07).
"""
from flask import Blueprint, jsonify
from app.web.routes.admin.helpers import apply_admin_guard
from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.taxonomy.models import Category, Source
from app.domains.product.models import Product
from app.domains.user.models import User
from app.domains.interaction.service.admin.analytics import get_interactions_breakdown, get_reaction_stats
from app.domains.interaction.models import Share
from sqlalchemy import func, select, cast, Date
from datetime import datetime, timedelta, timezone

bp = Blueprint("api_dashboard", __name__, url_prefix="/admin/dashboard")


apply_admin_guard(bp)





# ─────────────────────────────────────────────
# MAIN STATS ENDPOINT
# ─────────────────────────────────────────────

@bp.route("/stats", methods=["GET"])
def dashboard_stats():
    """Enhanced dashboard metrics, aggregates, distributions, and trends."""
    from app.application.analytics.admin import get_admin_dashboard_stats_data
    return jsonify(get_admin_dashboard_stats_data())


# ─────────────────────────────────────────────
# TOP CONTENT & PRODUCTS JSON ENDPOINTS (keep for backwards compat if needed)
# ─────────────────────────────────────────────

@bp.route("/top-contents", methods=["GET"])
def top_contents():
    """Top 5 content products by view count for the overview panel."""
    from app.application.analytics.admin import get_admin_top_contents
    return jsonify(get_admin_top_contents())


@bp.route("/top-products", methods=["GET"])
def top_items():
    """Top 5 products by click count for the overview panel."""
    from app.application.analytics.admin import get_admin_top_items
    return jsonify(get_admin_top_items())
