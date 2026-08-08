# app/admin/contents.py
"""
Admin content management endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- Safe sort-column allowlist in service layer (R-12).
- Extracted _serialize_content_row() helper (R-06).
- Extracted _delete_content_and_relations() helper shared by single and bulk delete (R-25).
- Removed unconditional per-page duplicate-title batch query (R-05).
- Removed ingestion_origin and object_id from serialized output (R-13).
- Shared pagination helpers from app.web.routes.admin.helpers (R-18, R-21).
- Moved build_content_inspect_data() to domain service (R-26).
"""
from flask import Blueprint, jsonify, request, render_template
from app.web.routes.admin.helpers import apply_admin_guard
from app.core.extensions import db
from app.web.routes.admin.helpers import parse_pagination_params, render_admin_rows_response
from app.domains.content.models import Content
from app.domains.content.service.query.filtering import get_content_paginated
from app.domains.content.service.admin import (
    load_admin_content_relations,
    delete_admin_content_and_relations,
    get_admin_content_metadata,
    get_admin_content_stats,
    get_admin_deduplication_groups,
    get_admin_content_inspect_raw,
)
from app.application.analytics.admin import (
    get_admin_content_dashboard_stats,
    get_admin_pipeline_stats,
)
from app.application.content.admin_serializers import serialize_content_row

from app.application.content.admin import (
    delete_content_workflow,
    toggle_publish_workflow,
    bulk_actions_workflow,
    retry_pipeline_workflow,
    get_content_inspect_workflow
)
from app.web.routes.admin.builders.content_builder import build_content_inspect_view_model


bp = Blueprint("api_content", __name__, url_prefix="/admin/contents")


apply_admin_guard(bp)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────





def _build_contents_query(args):
    """
    Build a filtered, sorted ORM query for content listing.
    """
    filters = args.to_dict() if hasattr(args, "to_dict") else dict(args)
    return get_content_paginated(
        filters=filters,
        sort_by=filters.get("sort_by", "").strip(),
        sort_dir=filters.get("sort_dir", "desc").strip(),
        page=filters.get("page", 1, type=int),
        per_page=filters.get("per_page", 20, type=int)
    )

def _load_content_relations(page_items, quality):
    """Batch-load polymorphic targets and duplicate titles for a page of contents."""
    return load_admin_content_relations(page_items, quality)


def _delete_content_and_relations(content: Content) -> None:
    """
    Delete a Content record plus all associated interactions and its
    polymorphic target. Does NOT commit — the caller is responsible.
    """
    delete_admin_content_and_relations(content)


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@bp.route("/meta", methods=["GET"])
def get_metadata():
    """Retrieve lists of categories, sections, sources, topics, and brands for dropdown filters."""
    return jsonify(get_admin_content_metadata())


@bp.route("/stats", methods=["GET"])
def get_stats():
    """Retrieve aggregate statistics for the summary bar."""
    return jsonify(get_admin_content_stats())


@bp.route("/dashboard", methods=["GET"])
def content_dashboard():
    """Render the high-level content analytics dashboard."""
    return render_template("admin/content_library/dashboard.html", stats=get_admin_content_dashboard_stats(), domain="content_dashboard")


@bp.route("/", methods=["GET"])
def list_contents():
    """Advanced content listing with filtering, search, pagination, and sorting."""
    page, per_page = parse_pagination_params(default_per_page=20)

    pagination, quality = get_content_paginated(
        filters=request.args,
        sort_by=request.args.get("sort_by", "").strip(),
        sort_dir=request.args.get("sort_dir", "desc").strip(),
        page=page,
        per_page=per_page
    )
    page_items = pagination.items

    # Batch-load polymorphic targets and duplicate titles
    targets_map, duplicate_titles = _load_content_relations(page_items, quality)

    serialized = [
        serialize_content_row(c, targets_map.get((c.object_type, c.object_id)), duplicate_titles)
        for c in page_items
    ]

    return jsonify({
        "products": serialized,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/<int:id>", methods=["DELETE"])
def delete_content(id):
    """Safely delete a content product and its interactions and polymorphic target."""
    success = delete_content_workflow(id)
    if not success:
        return jsonify({"error": "Content not found"}), 404

    return jsonify({"success": True, "message": "Content deleted successfully"})


@bp.route("/<int:id>/toggle-publish", methods=["POST"])
def toggle_publish(id):
    """Quickly toggle the publish status of a content product."""
    data = request.get_json() or {}
    action = data.get("action")
    
    try:
        content = toggle_publish_workflow(id, action)
        if not content:
            return jsonify({"error": "Content not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"success": True, "message": f"Content {'published' if content.is_published else 'unpublished'}."})


@bp.route("/rows", methods=["GET"])
def contents_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=20)

    pagination, quality = get_content_paginated(
        filters=request.args,
        sort_by=request.args.get("sort_by", "").strip(),
        sort_dir=request.args.get("sort_dir", "desc").strip(),
        page=page,
        per_page=per_page
    )
    page_items = pagination.items

    targets_map, duplicate_titles = _load_content_relations(page_items, quality)

    serialized = [
        serialize_content_row(c, targets_map.get((c.object_type, c.object_id)), duplicate_titles)
        for c in page_items
    ]

    return render_admin_rows_response(
        serialized, "content",
        total=pagination.total, pages=pagination.pages, page=pagination.page
    )



@bp.route("/<int:id>/inspect", methods=["GET"])
def inspect_content(id):
    """Render the inspect partial for a single content product."""
    aggregated_data = get_content_inspect_workflow(id)
    if not aggregated_data:
        return jsonify({"error": "Content not found"}), 404
        
    data = build_content_inspect_view_model(aggregated_data)
    data["domain"] = "contents"
    return render_template("admin/components/_inspect.html", **data)


@bp.route("/bulk", methods=["POST"])
def bulk_actions():
    """Bulk action endpoint: activate, deactivate, review, recategorize, delete."""
    data   = request.get_json() or {}
    action = data.get("action")
    ids    = data.get("ids", [])

    if not action or not ids:
        return jsonify({"error": "Invalid input parameters"}), 400

    category_id = data.get("category_id")
    try:
        count = bulk_actions_workflow(action, ids, category_id)
        if count == 0:
            return jsonify({"error": "No matching contents found"}), 404
        
        msg_map = {
            "activate": f"Activated {count} content products.",
            "deactivate": f"Deactivated {count} content products.",
            "publish": f"Published {count} content products.",
            "unpublish": f"Unpublished {count} content products.",
            "review": f"Marked {count} content products for review.",
            "recategorize": f"Moved {count} content products to new category.",
            "delete": f"Successfully deleted {count} content products and associated data."
        }
        return jsonify({"success": True, "message": msg_map.get(action, "Operation completed")})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

# ─────────────────────────────────────────────
# PIPELINE AUDIT
# ─────────────────────────────────────────────

@bp.route("/pipeline", methods=["GET"])
def pipeline_view():
    return render_template("admin/content_library/pipeline.html", domain="pipeline")

@bp.route("/pipeline/stats", methods=["GET"])
def pipeline_stats():
    return jsonify({"stats": get_admin_pipeline_stats()})


@bp.route("/pipeline/stats/partial", methods=["GET"])
def pipeline_stats_partial():
    """Return a server-rendered HTML partial for the pipeline stats table."""
    return render_template(
        "admin/content_library/_pipeline_stats_partial.html",
        stats=get_admin_pipeline_stats()
    )

@bp.route("/pipeline/retry", methods=["POST"])
def pipeline_retry():
    data = request.get_json() or {}
    origin = data.get("origin")
    retried = retry_pipeline_workflow(origin)
    return jsonify({"success": True, "retried": retried})

# ─────────────────────────────────────────────
# DEDUPLICATION WORKBENCH
# ─────────────────────────────────────────────

@bp.route("/deduplication", methods=["GET"])
def deduplication_view():
    return render_template("admin/content_library/deduplication.html", duplicate_groups=get_admin_deduplication_groups(), domain="deduplication")
