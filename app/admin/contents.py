# app/admin/contents.py
from flask import Blueprint, jsonify, request
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.content.models import Content, Article, Video, Post
from app.domains.taxonomy.models import Category, Section, Source
from app.domains.relationships import ArticleSource
from app.domains.interaction.models import Comment, Reaction, View
from sqlalchemy import func, or_, and_
from datetime import datetime

bp = Blueprint("api_content", __name__, url_prefix="/admin/contents")

# @bp.before_request
# @admin_required
# def require_admin():
#     """Ensure all contents endpoints require admin privilege."""
#     pass


@bp.route("/meta", methods=["GET"])
def get_metadata():
    """Retrieve lists of categories, sections, and sources for dropdown filters."""
    categories = db.session.query(Category).order_by(Category.name).all()
    sections = db.session.query(Section).order_by(Section.name).all()
    sources = db.session.query(Source).order_by(Source.name).all()
    
    return jsonify({
        "categories": [{"id": c.id, "slug": c.slug, "name": c.name} for c in categories],
        "sections": [{"id": s.id, "slug": s.slug, "name": s.name} for s in sections],
        "sources": [{"slug": s.slug, "name": s.name} for s in sources] + [
            {"slug": "youtube", "name": "YouTube"},
            {"slug": "reddit", "name": "Reddit"}
        ]
    })


@bp.route("/", methods=["GET"])
def list_contents():
    """Advanced content listing with filtering, search, pagination, and sorting."""
    # Pagination params
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    
    # Sorting params
    sort_by = request.args.get("sort_by", "id")
    sort_dir = request.args.get("sort_dir", "desc")
    
    # Filters
    search = request.args.get("search")
    section_slug = request.args.get("section")
    category_slug = request.args.get("category")
    object_type = request.args.get("type")
    source = request.args.get("source")
    status = request.args.get("status")
    active = request.args.get("active")
    published = request.args.get("published")
    date_type = request.args.get("date_type", "published_at")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    quality = request.args.get("quality")

    query = db.session.query(Content)

    # 1. Search filter (ID or title or preview text)
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        if search.strip().isdigit():
            query = query.filter(or_(Content.id == int(search.strip()), Content.title.ilike(search_term)))
        else:
            query = query.filter(or_(Content.title.ilike(search_term), Content.preview_text.ilike(search_term)))

    # 2. Section filter
    if section_slug:
        query = query.join(Content.section).filter(Section.slug == section_slug)

    # 3. Category filter
    if category_slug:
        if category_slug == "uncategorized":
            query = query.filter(or_(Content.category_id.is_(None), Content.category.has(Category.slug == "uncategorized")))
        else:
            query = query.join(Content.category).filter(Category.slug == category_slug)

    # 4. Content Type filter
    if object_type:
        query = query.filter(Content.object_type == object_type)

    # 5. Source filter
    if source:
        if source == "youtube":
            query = query.filter(Content.object_type == "video", Content.object_id.in_(
                db.session.query(Video.id).filter(Video.platform == source)
            ))
        elif source == "reddit":
            query = query.filter(Content.object_type == "post", Content.object_id.in_(
                db.session.query(Post.id).filter(Post.platform == source)
            ))
        else:
            query = query.filter(Content.object_type == "article", Content.object_id.in_(
                db.session.query(ArticleSource.article_id).join(Source).filter(Source.slug == source)
            ))

    # 6. Status filter (Article staged ingestion status)
    if status:
        query = query.filter(Content.object_type == "article", Content.object_id.in_(
            db.session.query(Article.id).filter(Article.status == status)
        ))

    # 7. Active status filter
    if active:
        query = query.filter(Content.is_active == (active.lower() == "true"))

    # 8. Published status filter
    if published:
        query = query.filter(Content.is_published == (published.lower() == "true"))

    # 9. Date Range filters
    date_col = Content.published_at if date_type == "published_at" else Content.ingested_at
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(date_col >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(date_col <= end_dt)
        except ValueError:
            pass

    # 10. Quality filters
    if quality:
        if quality == "missing_category":
            query = query.filter(or_(Content.category_id.is_(None), Content.category.has(Category.slug == "uncategorized")))
        elif quality == "missing_metadata":
            query = query.filter(or_(
                Content.title.is_(None), Content.title == "",
                Content.preview_text.is_(None), Content.preview_text == ""
            ))
        elif quality == "duplicate":
            dup_sub = db.session.query(Content.title).group_by(Content.title).having(func.count(Content.id) > 1).subquery()
            query = query.filter(Content.title.in_(dup_sub))

    # Apply Sorting
    sort_column = getattr(Content, sort_by, Content.published_at)
    if sort_dir.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    page_items = pagination.items

    # Batch load polymorphic targets
    ids_by_type = {}
    for c in page_items:
        ids_by_type.setdefault(c.object_type, set()).add(c.object_id)
        
    targets_map = {}
    for obj_type, ids in ids_by_type.items():
        if obj_type == "article":
            objs = db.session.query(Article).filter(Article.id.in_(list(ids))).all()
        elif obj_type == "video":
            objs = db.session.query(Video).filter(Video.id.in_(list(ids))).all()
        elif obj_type == "post":
            objs = db.session.query(Post).filter(Post.id.in_(list(ids))).all()
        for obj in objs:
            targets_map[(obj_type, obj.id)] = obj

    # Duplicate check for items on this page (against database)
    titles = [c.title for c in page_items if c.title]
    duplicate_titles = set()
    if titles:
        dup_rows = db.session.query(Content.title).filter(Content.title.in_(titles)).group_by(Content.title).having(func.count(Content.id) > 1).all()
        duplicate_titles = {r[0] for r in dup_rows}

    # Format output
    serialized = []
    for c in page_items:
        target = targets_map.get((c.object_type, c.object_id))
        
        # Determine source
        source_name = "Unknown"
        status_val = "complete"
        canonical_url = None
        
        if c.object_type == "article" and target:
            source_name = target.source_name
            status_val = target.status
            canonical_url = target.canonical_url
        elif c.object_type == "video" and target:
            source_name = target.platform.upper()
            canonical_url = target.url
        elif c.object_type == "post" and target:
            source_name = target.platform.upper()
            canonical_url = target.url

        # Check quality flags
        issues = []
        if not c.category_id or (c.category and c.category.slug == "uncategorized"):
            issues.append("missing_category")
        if not c.title or not c.preview_text:
            issues.append("missing_metadata")
        if c.title in duplicate_titles:
            issues.append("duplicate")

        serialized.append({
            "id": c.id,
            "title": c.title or f"Untitled ({c.object_type} #{c.id})",
            "object_type": c.object_type,
            "published_at": c.published_at.isoformat() if c.published_at else None,
            "ingested_at": c.ingested_at.isoformat() if c.ingested_at else None,
            "is_active": c.is_active,
            "is_published": c.is_published,
            "view_count": c.view_count or 0,
            "comment_count": c.comment_count or 0,
            "category_name": c.category.name if c.category else "Uncategorized",
            "category_id": c.category_id,
            "section_name": c.section.name if c.section else "Unassigned",
            "source_name": source_name,
            "status": status_val,
            "url": canonical_url,
            "quality_issues": issues
        })

    return jsonify({
        "items": serialized,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "per_page": pagination.per_page
    })


@bp.route("/<int:id>", methods=["DELETE"])
@admin_required
def delete_content(id):
    """Safely delete a content item and its polymorphic target, logs, reactions, and comments."""
    content = db.session.get(Content, id)
    if not content:
        return jsonify({"error": "Content not found"}), 404

    # Delete comments, reactions, and views for this content
    db.session.query(Comment).filter(Comment.target_type == "content", Comment.target_id == id).delete()
    db.session.query(Reaction).filter(Reaction.target_type == "content", Reaction.target_id == id).delete()
    db.session.query(View).filter(View.target_type == "content", View.target_id == id).delete()

    # Delete polymorphic target
    if content.object_type == "article":
        db.session.query(Article).filter(Article.id == content.object_id).delete()
    elif content.object_type == "video":
        db.session.query(Video).filter(Video.id == content.object_id).delete()
    elif content.object_type == "post":
        db.session.query(Post).filter(Post.id == content.object_id).delete()

    # Delete Content record itself
    db.session.delete(content)
    db.session.commit()

    return jsonify({"success": True, "message": "Content deleted successfully"})


@bp.route("/bulk", methods=["POST"])
@admin_required
def bulk_actions():
    """Bulk action endpoint supporting activate, deactivate, delete, and recategorize operations."""
    data = request.get_json() or {}
    action = data.get("action")
    ids = data.get("ids", [])
    
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
        # Mark as draft/un-published for moderation review
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
        # Bulk safe delete
        for c in contents:
            db.session.query(Comment).filter(Comment.target_type == "content", Comment.target_id == c.id).delete()
            db.session.query(Reaction).filter(Reaction.target_type == "content", Reaction.target_id == c.id).delete()
            db.session.query(View).filter(View.target_type == "content", View.target_id == c.id).delete()

            if c.object_type == "article":
                db.session.query(Article).filter(Article.id == c.object_id).delete()
            elif c.object_type == "video":
                db.session.query(Video).filter(Video.id == c.object_id).delete()
            elif c.object_type == "post":
                db.session.query(Post).filter(Post.id == c.object_id).delete()
            db.session.delete(c)

        db.session.commit()
        return jsonify({"success": True, "message": f"Successfully deleted {len(contents)} content items and associated files."})

    return jsonify({"error": "Unsupported bulk action"}), 400
