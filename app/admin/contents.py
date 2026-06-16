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
from flask import Blueprint, jsonify, request, render_template, make_response
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.content.models import Content, Article, Video, Post
from app.domains.taxonomy.models import Category, Section, Source
from app.domains.interaction.models import Comment, Reaction, View
from app.domains.relationships import ArticleSource
from app.admin.helpers import parse_pagination_params, parse_sort_params
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime

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
    "id":           Content.id,
    "published_at": Content.published_at,
    "ingested_at":  Content.ingested_at,
    "view_count":   Content.view_count,
    "comment_count": Content.comment_count,
    "title":        Content.title,
}


def _serialize_content_row(c, target, duplicate_titles: set) -> dict:
    """
    Serialize a single Content row for the admin listing.

    Args:
        c:                The Content ORM instance.
        target:           The polymorphic target (Article / Video / Post) or None.
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
    issues = []
    if not c.category_id or (c.category and c.category.slug == "uncategorized"):
        issues.append("missing_category")
    if not c.title or not c.preview_text:
        issues.append("missing_metadata")
    if c.title and c.title in duplicate_titles:
        issues.append("duplicate")

    return {
        "id":            c.id,
        "title":         c.title or f"Untitled ({c.object_type} #{c.id})",
        "object_type":   c.object_type,
        "published_at":  c.published_at.isoformat() if c.published_at else None,
        "ingested_at":   c.ingested_at.isoformat() if c.ingested_at else None,
        "is_active":     c.is_active,
        "is_published":  c.is_published,
        "view_count":    c.view_count or 0,
        "comment_count": c.comment_count or 0,
        "category_name": c.category.name if c.category else "Uncategorized",
        "category_id":   c.category_id,
        "section_name":  c.section.name if c.section else "Unassigned",
        "source_name":   source_name,
        "source_slug":   source_slug,
        "sources":   sources,
        "status":        status_val,
        "url":           canonical_url,
        "quality_issues": issues,
    }


def _delete_content_and_relations(content: Content) -> None:
    """
    Delete a Content record plus all associated interactions and its
    polymorphic target. Does NOT commit — the caller is responsible.
    Shared by single-delete and bulk-delete routes (R-25).
    """
    cid = content.id
    db.session.execute(
        Comment.__table__.delete().where(
            (Comment.target_type == "content") & (Comment.target_id == cid)
        )
    )
    db.session.execute(
        Reaction.__table__.delete().where(
            (Reaction.target_type == "content") & (Reaction.target_id == cid)
        )
    )
    db.session.execute(
        View.__table__.delete().where(
            (View.target_type == "content") & (View.target_id == cid)
        )
    )

    if content.object_type == "article":
        db.session.execute(Article.__table__.delete().where(Article.id == content.object_id))
    elif content.object_type == "video":
        db.session.execute(Video.__table__.delete().where(Video.id == content.object_id))
    elif content.object_type == "post":
        db.session.execute(Post.__table__.delete().where(Post.id == content.object_id))

    db.session.delete(content)


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@bp.route("/meta", methods=["GET"])
def get_metadata():
    """Retrieve lists of categories, sections, and sources for dropdown filters."""
    categories = db.session.execute(select(Category).order_by(Category.name)).scalars().all()
    sections   = db.session.execute(select(Section).order_by(Section.name)).scalars().all()
    sources    = db.session.execute(select(Source).order_by(Source.name)).scalars().all()

    return jsonify({
        "categories": [{"id": c.id, "slug": c.slug, "name": c.name} for c in categories],
        "sections":   [{"id": s.id, "slug": s.slug, "name": s.name} for s in sections],
        "sources":    [{"slug": s.slug, "name": s.name} for s in sources],
    })


@bp.route("/", methods=["GET"])
def list_contents():
    """Advanced content listing with filtering, search, pagination, and sorting."""
    page, per_page = parse_pagination_params(default_per_page=20)
    sort_col, sort_dir = parse_sort_params(_CONTENT_SORT_MAP, Content.published_at)

    # Filters
    search        = request.args.get("search")
    section_slug  = request.args.get("section")
    category_slug = request.args.get("category")
    object_type   = request.args.get("type")
    source        = request.args.get("source")
    status        = request.args.get("status")
    active        = request.args.get("active")
    published     = request.args.get("published")
    date_type     = request.args.get("date_type", "published_at")
    start_date    = request.args.get("start_date")
    end_date      = request.args.get("end_date")
    quality       = request.args.get("quality")

    query = db.session.query(Content).options(
        joinedload(Content.source),
        joinedload(Content.category),
        joinedload(Content.section),
    )

    # 1. Search filter
    if search and search.strip():
        term = f"%{search.strip()}%"
        if search.strip().isdigit():
            query = query.filter(or_(Content.id == int(search.strip()), Content.title.ilike(term)))
        else:
            query = query.filter(or_(Content.title.ilike(term), Content.preview_text.ilike(term)))

    # 2. Section filter
    if section_slug:
        query = query.join(Content.section).filter(Section.slug == section_slug)

    # 3. Category filter
    if category_slug:
        if category_slug == "uncategorized":
            query = query.filter(
                or_(Content.category_id.is_(None), Content.category.has(Category.slug == "uncategorized"))
            )
        else:
            query = query.join(Content.category).filter(Category.slug == category_slug)

    # 4. Type filter
    if object_type:
        query = query.filter(Content.object_type == object_type)

    # 5. Source filter
    if source:
        query = query.join(Content.source).filter(Source.slug == source)

    # 6. Article status filter
    if status:
        query = query.filter(
            Content.object_type == "article",
            Content.object_id.in_(db.session.query(Article.id).filter(Article.status == status)),
        )

    # 7. Active filter
    if active:
        query = query.filter(Content.is_active == (active.lower() == "true"))

    # 8. Published filter
    if published:
        query = query.filter(Content.is_published == (published.lower() == "true"))

    # 9. Date range filter
    date_col = Content.published_at if date_type == "published_at" else Content.ingested_at
    if start_date:
        try:
            query = query.filter(date_col >= datetime.strptime(start_date, "%Y-%m-%d"))
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(date_col <= end_dt)
        except ValueError:
            pass

    # 10. Quality filter
    if quality:
        if quality == "missing_category":
            query = query.filter(
                or_(Content.category_id.is_(None), Content.category.has(Category.slug == "uncategorized"))
            )
        elif quality == "missing_metadata":
            query = query.filter(
                or_(
                    Content.title.is_(None), Content.title == "",
                    Content.preview_text.is_(None), Content.preview_text == "",
                )
            )
        elif quality == "duplicate":
            # Subquery: titles that appear more than once
            dup_sub = (
                db.session.query(Content.title)
                .group_by(Content.title)
                .having(func.count(Content.id) > 1)
                .subquery()
            )
            query = query.filter(Content.title.in_(dup_sub))

    # Sorting (safe — from allowlist)
    query = query.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    page_items = pagination.items

    # Batch-load polymorphic targets
    ids_by_type: dict[str, set] = {}
    for c in page_items:
        ids_by_type.setdefault(c.object_type, set()).add(c.object_id)

    targets_map = {}
    for obj_type, ids in ids_by_type.items():
        model = {"article": Article, "video": Video, "post": Post}.get(obj_type)
        if model:
            stmt = select(model).where(model.id.in_(list(ids)))
            if model == Article:
                stmt = stmt.options(selectinload(Article.article_sources).joinedload(ArticleSource.source))
            objs = db.session.execute(stmt).scalars().all()
            for obj in objs:
                targets_map[(obj_type, obj.id)] = obj

    # Build duplicate-title set ONLY when the quality=duplicate filter is active.
    # Otherwise skip the extra GROUP BY+HAVING query entirely (R-05).
    duplicate_titles: set = set()
    if quality == "duplicate":
        titles = [c.title for c in page_items if c.title]
        if titles:
            dup_rows = db.session.execute(
                select(Content.title)
                .where(Content.title.in_(titles))
                .group_by(Content.title)
                .having(func.count(Content.id) > 1)
            ).scalars().all()
            duplicate_titles = set(dup_rows)

    serialized = [
        _serialize_content_row(c, targets_map.get((c.object_type, c.object_id)), duplicate_titles)
        for c in page_items
    ]

    return jsonify({
        "items":    serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
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


@bp.route("/rows", methods=["GET"])
def contents_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    from app.admin.helpers import parse_pagination_params, parse_sort_params
    page, per_page = parse_pagination_params(default_per_page=20)
    sort_col, sort_dir = parse_sort_params(_CONTENT_SORT_MAP, Content.published_at)

    search        = request.args.get("search")
    section_slug  = request.args.get("section")
    category_slug = request.args.get("category")
    object_type   = request.args.get("type")
    source        = request.args.get("source")
    status        = request.args.get("status")
    active        = request.args.get("active")
    published     = request.args.get("published")
    date_type     = request.args.get("date_type", "published_at")
    start_date    = request.args.get("start_date")
    end_date      = request.args.get("end_date")
    quality       = request.args.get("quality")

    query = db.session.query(Content).options(
        joinedload(Content.source),
        joinedload(Content.category),
        joinedload(Content.section),
    )

    if search and search.strip():
        term = f"%{search.strip()}%"
        if search.strip().isdigit():
            query = query.filter(or_(Content.id == int(search.strip()), Content.title.ilike(term)))
        else:
            query = query.filter(or_(Content.title.ilike(term), Content.preview_text.ilike(term)))
    if section_slug:
        query = query.join(Content.section).filter(Section.slug == section_slug)
    if category_slug:
        if category_slug == "uncategorized":
            query = query.filter(or_(Content.category_id.is_(None), Content.category.has(Category.slug == "uncategorized")))
        else:
            query = query.join(Content.category).filter(Category.slug == category_slug)
    if object_type:
        query = query.filter(Content.object_type == object_type)
    if source:
        query = query.join(Content.source).filter(Source.slug == source)
    if status:
        query = query.filter(Content.object_type == "article", Content.object_id.in_(db.session.query(Article.id).filter(Article.status == status)))
    if active:
        query = query.filter(Content.is_active == (active.lower() == "true"))
    if published:
        query = query.filter(Content.is_published == (published.lower() == "true"))
    date_col = Content.published_at if date_type == "published_at" else Content.ingested_at
    if start_date:
        try:
            query = query.filter(date_col >= datetime.strptime(start_date, "%Y-%m-%d"))
        except ValueError:
            pass
    if end_date:
        try:
            query = query.filter(date_col <= datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59))
        except ValueError:
            pass
    if quality:
        if quality == "missing_category":
            query = query.filter(or_(Content.category_id.is_(None), Content.category.has(Category.slug == "uncategorized")))
        elif quality == "missing_metadata":
            query = query.filter(or_(Content.title.is_(None), Content.title == "", Content.preview_text.is_(None), Content.preview_text == ""))
        elif quality == "duplicate":
            dup_sub = db.session.query(Content.title).group_by(Content.title).having(func.count(Content.id) > 1).subquery()
            query = query.filter(Content.title.in_(dup_sub))

    query = query.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    page_items = pagination.items

    ids_by_type: dict[str, set] = {}
    for c in page_items:
        ids_by_type.setdefault(c.object_type, set()).add(c.object_id)
    targets_map = {}
    for obj_type, ids in ids_by_type.items():
        model = {"article": Article, "video": Video, "post": Post}.get(obj_type)
        if model:
            stmt = select(model).where(model.id.in_(list(ids)))
            if model == Article:
                stmt = stmt.options(selectinload(Article.article_sources).joinedload(ArticleSource.source))
            objs = db.session.execute(stmt).scalars().all()
            for obj in objs:
                targets_map[(obj_type, obj.id)] = obj

    duplicate_titles: set = set()
    if quality == "duplicate":
        titles = [c.title for c in page_items if c.title]
        if titles:
            dup_rows = db.session.execute(
                select(Content.title).where(Content.title.in_(titles)).group_by(Content.title).having(func.count(Content.id) > 1)
            ).scalars().all()
            duplicate_titles = set(dup_rows)

    serialized = [
        _serialize_content_row(c, targets_map.get((c.object_type, c.object_id)), duplicate_titles)
        for c in page_items
    ]

    html = render_template("admin/control_panel/contents/_rows.html", items=serialized)
    resp = make_response(html)
    resp.headers["X-Total"] = pagination.total
    resp.headers["X-Pages"] = pagination.pages
    resp.headers["X-Page"]  = pagination.page
    return resp


@bp.route("/<int:id>/inspect", methods=["GET"])
def inspect_content(id):
    """Return server-rendered HTML for the content inspect modal body."""
    content = db.session.get(Content, id)
    if not content:
        return "<p class='text-muted'>Content not found.</p>", 404

    target = None
    if content.object_type in ("article", "video", "post"):
        model = {"article": Article, "video": Video, "post": Post}.get(content.object_type)
        if model:
            target = db.session.get(model, content.object_id)

    row = _serialize_content_row(content, target, set())
    return render_template("admin/control_panel/contents/_inspect.html", content=row)


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
