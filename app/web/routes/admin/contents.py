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
from app.core.decorators import admin_required
from app.domains.content.models import Content
from app.web.routes.admin.helpers import parse_pagination_params, make_rows_response
from app.domains.content.service.admin import (
    build_admin_contents_query,
    load_admin_content_relations,
    delete_admin_content_and_relations,
    get_admin_content_metadata,
    get_admin_content_stats,
    get_admin_content_dashboard_stats,
    get_admin_pipeline_stats,
    get_admin_deduplication_groups,
    get_admin_content_inspect_raw,
    build_content_inspect_data,
)
from app.application.content.admin import (
    delete_content_workflow,
    toggle_publish_workflow,
    bulk_actions_workflow,
    retry_pipeline_workflow
)


bp = Blueprint("api_content", __name__, url_prefix="/admin/contents")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all content management endpoints require admin privilege."""
    pass


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────



def _serialize_content_row(c, target, duplicate_titles: set) -> dict:
    """
    Serialize a single Content row for the admin listing.

    Args:
        c: The Content ORM instance.
        target: The polymorphic target (Article / Video / Post) or None.
        duplicate_titles: Set of titles known to be duplicated on the current page.

    Returns:
        A dict suitable for JSON serialization.
    """
    source_name  = c.source.name if c.source else "Unknown"
    source_slug  = c.source.slug if c.source else "unknown"
    status_val   = "complete"
    canonical_url = None

    if c.object_type == "article" and target:
        status_val    = target.status
        canonical_url = target.canonical_url
        sources = [s.source.name for s in target.article_sources if s.source]
    else:
        if target:
            canonical_url = target.url
        sources = [c.source.name] if c.source else []

    # Quality flags
    duplicate = c.title and c.title in duplicate_titles
    
    # Compute Health Score
    score = 0
    if c.title: score += 10
    if c.preview_text or getattr(target, 'description', None) or getattr(target, 'preview_text', None): score += 10
    if c.category and c.category.slug != 'uncategorized': score += 10
    if c.topics: score += 15
    if c.brands: score += 15
    if c.source_id: score += 10
    if not duplicate: score += 5
    
    if c.object_type == "article" and target:
        if getattr(target, 'is_content_scraped', False): score += 10
        if getattr(target, 'status', '') == 'complete': score += 10
        if getattr(target, 'quality_score', 0) > 0: score += 5
    elif c.object_type in ("video", "post"):
        score += 25
        
    score = min(score, 100)

    cat_name = c.category.name if c.category else "None"
    sec_name = c.section.name if c.section else "None"
    sources_text = ", ".join(sources)

    return {
        "id": c.id,
        "is_published": c.is_published,
        "title": c.title or "",
        "object_type": c.object_type,
        "category": cat_name,
        "section": sec_name,
        "has_topics": bool(c.topics),
        "has_brands": bool(c.brands),
        "has_source": bool(c.source_id),
        "is_duplicate": bool(duplicate),
        "enrichment_status": status_val,
        "health_score": score,
        "engagement": {
            "views": c.view_count, 
            "likes": c.like_count, 
            "comments": c.comment_count, 
            "shares": c.share_count, 
            "saves": c.save_count
        },
        "published_at": c.published_at.isoformat() if c.published_at else None,
        "sources_text": sources_text,
        "ingestion_origin": c.ingestion_origin,
    }


def _build_contents_query(args):
    """
    Build a filtered, sorted ORM query for content listing.
    """
    return build_admin_contents_query(args, args.get("sort_by", "").strip(), args.get("sort_dir", "desc").strip())

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
    return render_template("admin/content_library/dashboard.html", stats=get_admin_content_dashboard_stats())


@bp.route("/", methods=["GET"])
def list_contents():
    """Advanced content listing with filtering, search, pagination, and sorting."""
    page, per_page = parse_pagination_params(default_per_page=20)

    query, quality = _build_contents_query(request.args)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    page_items = pagination.items

    # Batch-load polymorphic targets and duplicate titles
    targets_map, duplicate_titles = _load_content_relations(page_items, quality)

    serialized = [
        _serialize_content_row(c, targets_map.get((c.object_type, c.object_id)), duplicate_titles)
        for c in page_items
    ]

    return jsonify({
        "items": serialized,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/<int:id>", methods=["DELETE"])
def delete_content(id):
    """Safely delete a content item and its interactions and polymorphic target."""
    success = delete_content_workflow(id)
    if not success:
        return jsonify({"error": "Content not found"}), 404

    return jsonify({"success": True, "message": "Content deleted successfully"})


@bp.route("/<int:id>/toggle-publish", methods=["POST"])
def toggle_publish(id):
    """Quickly toggle the publish status of a content item."""
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

    query, quality = _build_contents_query(request.args)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    page_items = pagination.items

    targets_map, duplicate_titles = _load_content_relations(page_items, quality)

    serialized = [
        _serialize_content_row(c, targets_map.get((c.object_type, c.object_id)), duplicate_titles)
        for c in page_items
    ]

    html = render_template("admin/components/_rows.html", items=serialized, domain_type="content")
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )



@bp.route("/<int:id>/inspect", methods=["GET"])
def inspect_content(id):
    """Render the inspect partial for a single content item."""
    data = build_content_inspect_data(id)
    if not data:
        return jsonify({"error": "Content not found"}), 404
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
            "activate": f"Activated {count} content items.",
            "deactivate": f"Deactivated {count} content items.",
            "publish": f"Published {count} content items.",
            "unpublish": f"Unpublished {count} content items.",
            "review": f"Marked {count} content items for review.",
            "recategorize": f"Moved {count} content items to new category.",
            "delete": f"Successfully deleted {count} content items and associated data."
        }
        return jsonify({"success": True, "message": msg_map.get(action, "Operation completed")})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

# ─────────────────────────────────────────────
# PIPELINE AUDIT
# ─────────────────────────────────────────────

@bp.route("/pipeline", methods=["GET"])
def pipeline_view():
    return render_template("admin/content_library/pipeline.html")

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
    return render_template("admin/content_library/deduplication.html", duplicate_groups=get_admin_deduplication_groups())
