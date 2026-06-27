# app/admin/contents.py
"""
Admin content management endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- Safe sort-column allowlist replacing unsafe getattr() (R-12).
- Extracted _serialize_content_row() helper (R-06).
- Extracted _delete_content_and_relations() helper shared by single and bulk delete (R-25).
- Removed unconditional per-page duplicate-title batch query (R-05).
- Removed ingestion_origin and object_id from serialized output (R-13).
- Shared pagination helpers from app.admin.helpers (R-18, R-21).
"""
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.content.models import Content, Article, Video, Post
from app.domains.taxonomy.models import Category, Section, Source
from app.domains.interaction.models import Comment, Reaction, View
from app.domains.relationships import ArticleSource
from app.admin.helpers import parse_pagination_params, parse_sort_params, make_rows_response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime
from app.domains.content.service.admin import (
    build_admin_contents_query,
    load_admin_content_relations,
    delete_admin_content_and_relations,
    get_admin_content_metadata,
    get_admin_content_stats,
    get_admin_content_dashboard_stats,
    get_admin_pipeline_stats,
    retry_admin_pipeline,
    get_admin_deduplication_groups,
    get_admin_content_inspect_raw
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

# Safe allowlist for sort columns (R-12)
_CONTENT_SORT_MAP = {
    "id": Content.id,
    "published_at": Content.published_at,
    "ingested_at": Content.ingested_at,
    "view_count": Content.view_count,
    "like_count": Content.like_count,
    "comment_count": Content.comment_count,
    "share_count": Content.share_count,
    "save_count": Content.save_count,
    "score": Content.score,
    "title": Content.title,
}


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
    
    health_badges = []
    
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
    score_class = "badge-health-high" if score >= 80 else ("badge-health-medium" if score >= 50 else "badge-health-low")
    health_badges.append({"value": f"{score}% Health", "badge_class": f"{score_class} badge-compact"})

    if not c.topics:
        health_badges.append({"value": "No Topics", "badge_class": "status-badge inactive flex items-center gap-1", "title": "No Topics", "icon": "⚠️"})
    if not c.brands:
        health_badges.append({"value": "No Brands", "badge_class": "status-badge inactive flex items-center gap-1", "title": "No Brands", "icon": "⚠️"})
    if not c.source_id:
        health_badges.append({"value": "No Source", "badge_class": "status-badge inactive flex items-center gap-1", "title": "No Source", "icon": "🔴"})
    if c.object_type == "article" and target and target.status == "failed":
        health_badges.append({"value": "Failed", "badge_class": "status-badge inactive flex items-center gap-1", "title": "Enrichment Failed", "icon": "⛔"})
    if duplicate:
        health_badges.append({"value": "Duplicate", "badge_class": "status-badge user flex items-center gap-1", "title": "Duplicate Title", "icon": "👯"})
        
    title_data = {"value": c.title or "", "badges": health_badges}

    # Engagement
    engagement_data = {"views": c.view_count, "likes": c.like_count, "comments": c.comment_count, "shares": c.share_count, "saves": c.save_count}

    # Classification
    cat_name = c.category.name if c.category else "None"
    sec_name = c.section.name if c.section else "None"
    classification_data = {
        "type": c.object_type,
        "category": cat_name,
        "section": sec_name
    }

    # Sources
    sources_text = ", ".join(sources)
    sources_data = {
        "text": sources_text,
        "origin_chip": c.ingestion_origin
    }

    # Status
    pub_status = {"value": "Live", "badge_class": "status-badge active w-fit"} if c.is_published else {"value": "Draft", "badge_class": "status-badge inactive w-fit"}
    action_btn = {
        "action": "unpublish" if c.is_published else "publish",
        "id": c.id,
        "label": "Unpublish" if c.is_published else "Publish",
        "class": "dashboard-btn-danger" if c.is_published else "dashboard-btn-primary"
    }
    status_data = {"status": pub_status, "action": action_btn}

    return {
        "id": c.id,
        "is_published": c.is_published,
        "title": title_data,
        "classification": classification_data,
        "engagement": engagement_data,
        "published-at": c.published_at.isoformat() if c.published_at else None,
        "sources": sources_data,
        "status": status_data,
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
    content = db.session.get(Content, id)
    if not content:
        return jsonify({"error": "Content not found"}), 404

    _delete_content_and_relations(content)
    db.session.commit()
    return jsonify({"success": True, "message": "Content deleted successfully"})


@bp.route("/<int:id>/toggle-publish", methods=["POST"])
def toggle_publish(id):
    """Quickly toggle the publish status of a content item."""
    content = db.session.get(Content, id)
    if not content:
        return jsonify({"error": "Content not found"}), 404

    data = request.get_json() or {}
    action = data.get("action")
    if action == "publish":
        content.is_published = True
    elif action == "unpublish":
        content.is_published = False
    else:
        return jsonify({"error": "Invalid action parameter"}), 400

    db.session.commit()
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
    data = build_content_inspect_data(id)
    if not data:
        return jsonify({"error": "Content not found"}), 404
    data["domain"] = "contents"
    return render_template("admin/components/_inspect.html", **data)


def build_content_inspect_data(id):
    """Return dictionary of data needed for the content inspect/detail view."""
    raw_data = get_admin_content_inspect_raw(id)
    if not raw_data:
        return None
    
    content = raw_data["content"]
    target = raw_data["target"]

    sources = []
    if content.object_type == "article" and target:
        sources = [s.source.name for s in target.sorted_source_relations if s.source]
    else:
        sources = [content.source.name] if content.source else []

    status_val = target.status if target and hasattr(target, "status") else "complete"

    from app.admin.helpers import format_datetime
    from app.admin.tables import get_inspect_table
    
    from app.domains.interaction.service.scoring import get_content_engagement_score
    engagement_score = get_content_engagement_score(content.id)
    
    sec_slug = content.section.slug if content.section else ''
    cat_slug = content.category.slug if content.category else ''
    sec_name = content.section.name if content.section else 'Unassigned'
    cat_name = content.category.name if content.category else 'Uncategorized'
    
    taxonomy_breadcrumb = [
        {"label": sec_name, "link": f'/admin/contents?section={sec_slug}'},
        {"label": cat_name, "link": f'/admin/contents?category={cat_slug}'}
    ]

    data = {
        "id": f"#{content.id}",
        "title": content.title or "—",
        "type": content.object_type,
        "taxonomy path": {"value": taxonomy_breadcrumb, "is_breadcrumb": True},
        "engagement score": str(engagement_score),
        "related brands": ", ".join(b.name for b in content.brands) if content.brands else "—",
        "related topics": ", ".join(t.name for t in content.topics) if content.topics else "—",
        "mentioned products": ", ".join(i.name for i in content.linked_items) if content.linked_items else "—",
        "attributes": ", ".join(a.name for a in content.attributes) if content.attributes else "—",
        "available sources": ", ".join(sources) if sources else "—",
        "primary source": content.source.name if content.source else "—",
        "acquired via": content.ingestion_origin if content.ingestion_origin else "—",
        "published at": format_datetime(content.published_at) or "—",
        "ingested at": format_datetime(content.ingested_at) or "—",
        "enrichment status": status_val,
        "status": "Live Index" if content.is_published else "Draft",
        "renderation status": "Active" if content.is_active else "Inactive",
        "views": "{:,}".format(content.view_count or 0),
        "likes": "{:,}".format(content.like_count or 0),
        "dislikes": "{:,}".format(content.dislike_count or 0),
        "comments": "{:,}".format(content.comment_count or 0),
        "shares": "{:,}".format(content.share_count or 0),
        "saves": "{:,}".format(content.save_count or 0),
        "intent": content.intent.name if content.intent else "—",
        "gender": content.gender.name if content.gender else "—",
        "price tier": content.price_tier.name if content.price_tier else "—",
        "base score": str(content.score or 0),
        "review score": str(content.review_score or 0),
    }

    if content.object_type == "video" and target:
        data["platform"] = target.platform
        data["channel"] = target.channel_name or "—"
    elif content.object_type == "post" and target:
        data["platform"] = target.platform
        data["author"] = target.author or "—"
        data["subreddit"] = target.subreddit or "—"
        data["platform upvotes"] = str(target.upvotes or 0)
        data["platform comments"] = str(target.comments_count or 0)
    elif content.object_type == "article" and target:
        data["is scraped"] = "Yes" if target.is_content_scraped else "No"
        data["word count"] = "{:,}".format(target.word_count or 0)
        data["read time"] = f"{target.read_time_minutes} min" if hasattr(target, 'read_time_minutes') else "—"
        data["article quality score"] = str(target.quality_score or 0)
        data["last enrichment attempt"] = format_datetime(target.last_enrichment_attempt) if target.last_enrichment_attempt else "—"

    inspect_table = get_inspect_table("contents", data)
    
    if target and hasattr(target, "url") and target.url:
        inspect_table["Related Metadata"].append(
            {"label": "Source Link", "value": {"label": "View Original Link", "link": target.url, "external": True}, "is_link": True}
        )
        
    article_sources_data = []
    if content.object_type == "article" and target and target.article_sources:
        article_sources_data = target.article_sources
        
    recent_comments = sorted(content.comments, key=lambda c: c.created_at or datetime.min, reverse=True)[:3]
    if recent_comments:
        if "Related Metadata" not in inspect_table:
            inspect_table["Related Metadata"] = []
        for idx, c in enumerate(recent_comments):
            user_name = c.user.name if c.user else f"User #{c.user_id}"
            preview = c.content[:100] + ("..." if len(c.content) > 100 else "")
            inspect_table["Related Metadata"].append({
                "label": f"Recent Comment {idx+1}",
                "value": {"label": user_name, "detail": preview},
                "is_labeled": True
            })

    actions = [
        {
            "label": "Delete Content",
            "action_type": "delete",
            "icon": "🗑",
            "extra_class": "user-action-delete",
            "attrs": {"data-action": "delete-content", "data-id": content.id, "data-title": (content.title or '')}
        }
    ]

    from app.domains.distribution.services import get_distribution_history
    distribution_history = get_distribution_history("content", id)
        
    return {
        "inspect_table": inspect_table,
        "article_sources": article_sources_data,
        "distribution_history": distribution_history,
        "actions": actions,
        "inspect_id": content.id
    }


@bp.route("/bulk", methods=["POST"])
def bulk_actions():
    """Bulk action endpoint: activate, deactivate, review, recategorize, delete."""
    data   = request.get_json() or {}
    action = data.get("action")
    ids    = data.get("ids", [])

    if not action or not ids:
        return jsonify({"error": "Invalid input parameters"}), 400

    contents = db.session.query(Content).filter(Content.id.in_(ids)).all()
    if not contents:
        return jsonify({"error": "No matching contents found"}), 404

    if action == "activate":
        for c in contents:
            c.is_active = True
        db.session.commit()
        return jsonify({"success": True, "message": f"Activated {len(contents)} content items."})

    elif action == "deactivate":
        for c in contents:
            c.is_active = False
        db.session.commit()
        return jsonify({"success": True, "message": f"Deactivated {len(contents)} content items."})

    elif action == "publish":
        for c in contents:
            c.is_published = True
        db.session.commit()
        return jsonify({"success": True, "message": f"Published {len(contents)} content items."})

    elif action == "unpublish":
        for c in contents:
            c.is_published = False
        db.session.commit()
        return jsonify({"success": True, "message": f"Unpublished {len(contents)} content items."})

    elif action == "review":
        for c in contents:
            c.is_published = False
        db.session.commit()
        return jsonify({"success": True, "message": f"Marked {len(contents)} content items for review."})

    elif action == "recategorize":
        category_id = data.get("category_id")
        if category_id is None:
            return jsonify({"error": "Category ID is required for recategorize action"}), 400
        category = db.session.get(Category, int(category_id))
        if not category:
            return jsonify({"error": "Target category not found"}), 404
        for c in contents:
            c.category_id = category.id
        db.session.commit()
        return jsonify({"success": True, "message": f"Moved {len(contents)} content items to category '{category.name}'."})

    elif action == "delete":
        # Reuse shared helper — single source of truth for deletion logic (R-25)
        for c in contents:
            _delete_content_and_relations(c)
        db.session.commit()
        return jsonify({"success": True, "message": f"Successfully deleted {len(contents)} content items and associated data."})

    return jsonify({"error": "Unsupported bulk action"}), 400

# ─────────────────────────────────────────────
# PIPELINE AUDIT
# ─────────────────────────────────────────────

@bp.route("/pipeline", methods=["GET"])
@admin_required
def pipeline_view():
    return render_template("admin/content_library/pipeline.html")

@bp.route("/pipeline/stats", methods=["GET"])
@admin_required
def pipeline_stats():
    return jsonify({"stats": get_admin_pipeline_stats()})


@bp.route("/pipeline/stats/partial", methods=["GET"])
@admin_required
def pipeline_stats_partial():
    """Return a server-rendered HTML partial for the pipeline stats table."""
    return render_template(
        "admin/content_library/_pipeline_stats_partial.html",
        stats=get_admin_pipeline_stats()
    )

@bp.route("/pipeline/retry", methods=["POST"])
@admin_required
def pipeline_retry():
    data = request.get_json() or {}
    origin = data.get("origin")
    retried = retry_admin_pipeline(origin)
    db.session.commit()
    return jsonify({"success": True, "retried": retried})

# ─────────────────────────────────────────────
# DEDUPLICATION WORKBENCH
# ─────────────────────────────────────────────

@bp.route("/deduplication", methods=["GET"])
@admin_required
def deduplication_view():
    return render_template("admin/content_library/deduplication.html", duplicate_groups=get_admin_deduplication_groups())
