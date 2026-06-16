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
from flask import Blueprint, jsonify, current_app, request, render_template
from app.core.extensions import db, cache
from app.core.decorators import admin_required
from app.admin.ingestions import get_integrations_status_data, get_integrations_logs_data

bp = Blueprint("api_system", __name__, url_prefix="/admin/system")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all system configuration routes are strictly admin-only."""
    pass


def _build_system_info() -> list:
    """Build the system info list shared by the JSON and HTML widget endpoints."""
    try:
        db_type = db.engine.name if db.engine else "Unknown"
    except Exception:
        db_type = "Unknown"
    version = current_app.config.get("APP_VERSION", "1.3.0")
    return [
        {"label": "Backend Status", "value": "online", "status": "online"},
        {"label": "Version",        "value": version},
        {"label": "Environment",    "value": current_app.config.get("ENV", "Development")},
        {"label": "Python",         "value": sys.version.split()[0]},
        {"label": "Flask",          "value": flask.__version__},
        {"label": "Database",       "value": db_type.capitalize()},
    ]


@bp.route("/info", methods=["GET"])
def system_info():
    """Return backend status metrics and environment configurations."""
    return jsonify(_build_system_info())


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


# ─────────────────────────────────────────────
# WIDGET ENDPOINTS
# ─────────────────────────────────────────────

@bp.route("/widget/info", methods=["GET"])
def widget_system_info():
    info = _build_system_info()
    return render_template("admin/control_panel/settings/widgets/_info.html", info=info)


@bp.route("/widget/integrations", methods=["GET"])
def widget_integrations():
    data = get_integrations_status_data()
    from datetime import datetime
    for intg in data:
        last_fetch = intg.get("last_fetch")
        if last_fetch:
            try:
                dt = datetime.fromisoformat(last_fetch)
                intg["last_fetch_formatted"] = dt.strftime("%m/%d/%Y, %I:%M:%S %p")
            except Exception:
                intg["last_fetch_formatted"] = last_fetch
        else:
            intg["last_fetch_formatted"] = "Never"
    return render_template("admin/control_panel/settings/widgets/_integrations.html", data=data)


@bp.route("/widget/ingestion-logs", methods=["GET"])
def widget_ingestion_logs():
    log_type = request.args.get("type", "all")
    data = get_integrations_logs_data()
    
    if log_type != "all":
        data = [log for log in data if log.get("type") == log_type]
        
    from datetime import datetime
    for log in data:
        log_time = log.get("time")
        if log_time:
            try:
                dt = datetime.fromisoformat(log_time)
                log["time_formatted"] = dt.strftime("%m/%d/%Y, %I:%M:%S %p")
            except Exception:
                log["time_formatted"] = log_time
        else:
            log["time_formatted"] = "Recently"
            
    return render_template("admin/control_panel/settings/widgets/_ingestion_logs.html", logs=data)
