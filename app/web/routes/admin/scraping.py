# app/web/routes/admin/scraping.py
import threading
from flask import Blueprint, jsonify, request, render_template
from app.web.routes.admin.helpers import apply_admin_guard
from app.shared.utils.task_tracker import TaskTracker

bp = Blueprint("api_scraping", __name__, url_prefix="/admin/scraping")
apply_admin_guard(bp)

@bp.route("/control", methods=["GET"])
def scraping_control():
    """Render the Scraping Control Panel."""
    return render_template("admin/pages/scraping_control.html")

@bp.route("/api/run", methods=["POST"])
def run_scraping():
    """Trigger the background scraping task."""
    from app.application.content.workflows.enrichment import enrich_discovered_articles
    
    req_data = request.get_json() or {}
    try:
        limit = int(req_data.get("limit", 50))
    except ValueError:
        limit = 50
    
    tracker = TaskTracker()
    task_id = tracker.create_task(
        name="scraping_batch",
        description=f"Scraping up to {limit} articles"
    )

    def _background_scrape(t_id, lmt):
        from app.core.factory import create_app
        # We need an app context to run DB queries
        app = create_app()
        with app.app_context():
            tracker.update_status(t_id, "running", progress=10)
            try:
                results = enrich_discovered_articles(limit=lmt)
                tracker.update_status(t_id, "completed", progress=100, result=results)
            except Exception as e:
                tracker.update_status(t_id, "failed", error=str(e))

    thread = threading.Thread(target=_background_scrape, args=(task_id, limit))
    thread.daemon = True
    thread.start()

    return jsonify({"task_id": task_id, "status": "started"})

@bp.route("/api/task/<task_id>", methods=["GET"])
def api_task_status(task_id):
    """Poll the status of a scraping task."""
    tracker = TaskTracker()
    task = tracker.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)
