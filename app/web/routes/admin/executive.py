from flask import Blueprint, render_template, jsonify
from app.core.decorators import admin_required
from app.domains.analytics import get_executive_summary

bp = Blueprint("admin_executive", __name__, url_prefix="/admin/executive")

@bp.before_request
@admin_required
def require_admin():
    pass

@bp.route("/", methods=["GET"])
def index():
    summary_data = get_executive_summary()
    return render_template("admin/executive/dashboard.html", summary=summary_data)

@bp.route("/digest", methods=["GET"])
def digest():
    summary_data = get_executive_summary()
    return jsonify({
        "status": "success",
        "digest": summary_data
    })
