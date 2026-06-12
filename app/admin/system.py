# app/admin/system.py
"""
Admin system configuration and status endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- Version string sourced from app config instead of a hardcoded literal (R-11).
- HTML markup removed from JSON response; `status` is now a plain string (R-11).
"""
import os
import sys
import flask
from flask import Blueprint, jsonify, current_app, request
from app.core.extensions import db, cache
from app.core.decorators import admin_required

bp = Blueprint("api_system", __name__, url_prefix="/admin/system")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all system configuration routes are strictly admin-only."""
    pass


@bp.route("/info", methods=["GET"])
def system_info():
    """Return backend status metrics and environment configurations."""
    try:
        db_type = db.engine.name if db.engine else "Unknown"
    except Exception:
        db_type = "Unknown"

    # Version sourced from config (set e.g. via APP_VERSION env var) — no hardcoding (R-11)
    version = current_app.config.get("APP_VERSION", "1.3.0")

    return jsonify([
        {"label": "Backend Status", "value": "online", "status": "online"},
        {"label": "Version",        "value": version},
        {"label": "Environment",    "value": current_app.config.get("ENV", "Development")},
        {"label": "Python",         "value": sys.version.split()[0]},
        {"label": "Flask",          "value": flask.__version__},
        {"label": "Database",       "value": db_type.capitalize()},
    ])


@bp.route("/cache", methods=["DELETE"])
def clear_cache():
    """Clear server-side page and query caches."""
    try:
        cache.clear()
        return jsonify({"success": True, "message": "Cache cleared successfully."}), 200
    except Exception as e:
        current_app.logger.error(f"[SYSTEM] Cache clear failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/maintenance", methods=["GET"])
def get_maintenance():
    """Check if maintenance mode is active."""
    lock_file = os.path.join(current_app.instance_path, "maintenance.lock")
    return jsonify({"enabled": os.path.exists(lock_file)})


@bp.route("/maintenance", methods=["POST"])
def toggle_maintenance():
    """Toggle maintenance mode state by managing the maintenance lock file."""
    try:
        data    = request.get_json() or {}
        enabled = data.get("enabled", False)
        os.makedirs(current_app.instance_path, exist_ok=True)
        lock_file = os.path.join(current_app.instance_path, "maintenance.lock")

        if enabled:
            with open(lock_file, "w") as f:
                f.write("maintenance")
            current_app.logger.warning("[SYSTEM] Maintenance mode has been enabled.")
        else:
            if os.path.exists(lock_file):
                os.remove(lock_file)
            current_app.logger.info("[SYSTEM] Maintenance mode has been disabled.")

        return jsonify({"success": True, "enabled": enabled})
    except Exception as e:
        current_app.logger.error(f"[SYSTEM] Toggle maintenance failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/reset", methods=["POST"])
def reset_system():
    """Wipe external API logs, stats and cache to reset state."""
    from app.domains.external.models import APIUsage, LastAPIFetch
    try:
        db.session.execute(LastAPIFetch.__table__.delete())
        db.session.execute(APIUsage.__table__.delete())
        db.session.commit()
        cache.clear()
        current_app.logger.warning("[SYSTEM] Administrative system state reset has been executed.")
        return jsonify({"success": True, "message": "System logs, statistics, and cache cleared successfully."}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[SYSTEM] System reset failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
