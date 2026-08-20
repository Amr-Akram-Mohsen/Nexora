"""
Admin ingestion monitoring endpoints.
"""
import json
import os
import threading
from flask import Blueprint, jsonify, request, render_template, current_app
from app.web.routes.admin.helpers import apply_admin_guard
from app.domains.external.service.admin import (
    get_admin_integrations_status_data,
    get_admin_integrations_logs_data,
)
from app.shared.utils.task_tracker import TaskTracker

bp = Blueprint("api_ingestion", __name__, url_prefix="/admin/ingestions")
apply_admin_guard(bp)


@bp.route("/status", methods=["GET"])
def integrations_status():
    """Return live API usage and last-fetch data for all known ingestion sources."""
    data = get_admin_integrations_status_data()
    if request.args.get('format') == 'html':
        return render_template("admin/components/rows/_ingestion_status_cards.html", products=data)

    return jsonify(data)


@bp.route("/logs", methods=["GET"])
def integrations_logs():
    """Return the 15 most recent ingestion log entries."""
    data = get_admin_integrations_logs_data()
    if request.args.get('format') == 'html':
        return render_template("admin/components/_rows.html", products=data, domain_type="ingestion_log", empty_text="No recent events.")

    return jsonify(data)


@bp.route("/control", methods=["GET"])
def ingestion_control():
    """Render the Ingestion Control Panel."""
    return render_template("admin/pages/ingestion_control.html")


@bp.route("/api/helpers", methods=["GET"])
def api_helpers():
    """Return cache states to populate the UI helpers."""
    def safe_read_json(filename):
        path = os.path.join(current_app.instance_path, "cache", filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    return jsonify({
        "discovery_brands_rotation": safe_read_json("discovery_brands_rotation.json"),
        "category_batch_rotation": safe_read_json("category_batch_rotation.json"),
        "query_cursor_newsapi_ai": safe_read_json("query_cursor_state/newsapi_ai.json"),
        "query_cursor_youtube": safe_read_json("query_cursor_state/youtube.json"),
    })


@bp.route("/api/task/<task_id>", methods=["GET"])
def api_task_status(task_id):
    tracker = TaskTracker()
    task = tracker.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


def _background_run(app_obj, task_id, source_name, kwargs):
    with app_obj.app_context():
        tracker = TaskTracker()
        tracker.update_status(task_id, "processing")
        try:
            from app.integrations.content.core.run_fetcher import run_fetcher
            obj_type = "video" if source_name == "youtube" else "article"
            result = run_fetcher(source_name=source_name, object_type=obj_type, **kwargs)
            tracker.update_status(task_id, "completed", result=result)
        except Exception as exc:
            tracker.update_status(task_id, "error", error=str(exc))


@bp.route("/api/run/<source_name>", methods=["POST"])
def api_run_ingestion(source_name):
    data = request.get_json() or {}

    dry_run = data.get("dry_run", False)
    target_section = data.get("target_section")
    target_category = data.get("target_category")
    limit = data.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
        except ValueError:
            limit = None

    profile_overrides = data.get("profile_overrides", {})

    kwargs = {
        "target_section": target_section,
        "target_category": target_category,
        "profile_overrides": profile_overrides,
        "dry_run": dry_run,
        "limit": limit
    }

    if dry_run:
        from app.integrations.content.core.run_fetcher import run_fetcher
        obj_type = "video" if source_name == "youtube" else "article"
        result = run_fetcher(source_name=source_name, object_type=obj_type, **kwargs)
        return jsonify(result)

    tracker = TaskTracker()
    task_id = tracker.create_task(source_name, kwargs)

    app_obj = current_app._get_current_object()
    thread = threading.Thread(target=_background_run, args=(app_obj, task_id, source_name, kwargs))
    thread.daemon = True
    thread.start()

    return jsonify({"status": "started", "task_id": task_id}), 202

