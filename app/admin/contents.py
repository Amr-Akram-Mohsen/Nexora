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
    views = f"{c.view_count:,}" if c.view_count else "0"
    likes = f"{c.like_count:,}" if c.like_count else "0"
    comments = f"{c.comment_count:,}" if c.comment_count else "0"
    engagement_data = [
        {"icon": '<i class="fas fa-eye"></i>', "value": f"{views} views", "title": "Views"},
        {"icon": '<i class="fas fa-comment"></i>', "value": f"{comments} comments", "title": "Comments"},
        {"icon": '<i class="fas fa-heart"></i>', "value": f"{likes} likes", "title": "Likes"}
    ]

    # Classification
    cat_name = c.category.name if c.category else "None"
    sec_name = c.section.name if c.section else "None"
    classification_data = {
        "type": c.object_type,
        "category": f"📁 {cat_name}",
        "section": f"🏷️ {sec_name}"
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

    Reads all filter params from *args* (a dict-like, e.g. ``request.args``).
    Returns an ORM query ready for ``.paginate()`` — caller is responsible
    for pagination and serialization.

    Shared between ``list_contents`` (JSON) and ``contents_rows`` (HTML partial)
    so filter logic only lives in one place.
    """
    sort_col, sort_dir = parse_sort_params(_CONTENT_SORT_MAP, Content.published_at)

    search        = args.get("search")
    section_slug  = args.get("section")
    category_slug = args.get("category")
    object_type   = args.get("type")
    source        = args.get("source")
    status        = args.get("status")
    active        = args.get("active")
    published     = args.get("published")
    date_type     = args.get("date_type", "published_at")
    start_date    = args.get("start_date")
    end_date      = args.get("end_date")
    quality       = args.get("quality")

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
            query = query.filter(
                or_(Content.category_id.is_(None), Content.category.has(Category.slug == "uncategorized"))
            )
        else:
            query = query.join(Content.category).filter(Category.slug == category_slug)
    if object_type:
        query = query.filter(Content.object_type == object_type)
    if source:
        query = query.join(Content.source).filter(Source.slug == source)
    if status:
        query = query.filter(
            Content.object_type == "article",
            Content.object_id.in_(db.session.query(Article.id).filter(Article.status == status)),
        )
    if active:
        query = query.filter(Content.is_active == (active.lower() == "true"))
    if published:
        query = query.filter(Content.is_published == (published.lower() == "true"))

    topic_slug = args.get("topic")
    brand_slug = args.get("brand")
    origin     = args.get("ingestion_origin")
    intent_slug = args.get("intent")
    gender_slug = args.get("gender")
    price_tier_slug = args.get("price_tier")

    if topic_slug:
        if topic_slug == "none":
            query = query.filter(~Content.topics.any())
        else:
            query = query.filter(Content.topics.any(slug=topic_slug))
    if brand_slug:
        if brand_slug == "none":
            query = query.filter(~Content.brands.any())
        else:
            query = query.filter(Content.brands.any(slug=brand_slug))
    if origin:
        query = query.filter(Content.ingestion_origin == origin)
        
    if intent_slug:
        query = query.filter(Content.intent.has(slug=intent_slug))
    if gender_slug:
        query = query.filter(Content.gender.has(slug=gender_slug))
    if price_tier_slug:
        query = query.filter(Content.price_tier.has(slug=price_tier_slug))

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
            dup_sub = (
                db.session.query(Content.title)
                .group_by(Content.title)
                .having(func.count(Content.id) > 1)
                .subquery()
            )
            query = query.filter(Content.title.in_(dup_sub))
        elif quality == "missing_topics":
            query = query.filter(~Content.topics.any())
        elif quality == "missing_brands":
            query = query.filter(~Content.brands.any())
        elif quality == "missing_source":
            query = query.filter(Content.source_id.is_(None))
        elif quality == "enrichment_failed":
            query = query.filter(
                Content.object_type == "article",
                Content.object_id.in_(db.session.query(Article.id).filter(Article.status == "failed"))
            )

    query = query.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())
    return query, quality

def _load_content_relations(page_items, quality):
    """Batch-load polymorphic targets and duplicate titles for a page of contents."""
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
                select(Content.title)
                .where(Content.title.in_(titles))
                .group_by(Content.title)
                .having(func.count(Content.id) > 1)
            ).scalars().all()
            duplicate_titles = set(dup_rows)
            
    return targets_map, duplicate_titles


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
    """Retrieve lists of categories, sections, sources, topics, and brands for dropdown filters."""
    from app.domains.taxonomy.models import Topic, Brand, IntentFacet, GenderFacet, PriceTierFacet
    
    categories = db.session.execute(select(Category).order_by(Category.name)).scalars().all()
    sections   = db.session.execute(select(Section).order_by(Section.name)).scalars().all()
    sources    = db.session.execute(select(Source).order_by(Source.name)).scalars().all()
    topics     = db.session.execute(select(Topic).order_by(Topic.name)).scalars().all()
    brands     = db.session.execute(select(Brand).order_by(Brand.name)).scalars().all()
    
    intents    = db.session.execute(select(IntentFacet).order_by(IntentFacet.name)).scalars().all()
    genders    = db.session.execute(select(GenderFacet).order_by(GenderFacet.name)).scalars().all()
    price_tiers= db.session.execute(select(PriceTierFacet).order_by(PriceTierFacet.name)).scalars().all()
    
    # Get distinct ingestion origins
    origins = db.session.execute(select(Content.ingestion_origin).filter(Content.ingestion_origin.is_not(None)).distinct()).scalars().all()

    return jsonify({
        "categories": [{"id": c.id, "slug": c.slug, "name": c.name} for c in categories],
        "sections": [{"id": s.id, "slug": s.slug, "name": s.name} for s in sections],
        "sources": [{"slug": s.slug, "name": s.name} for s in sources],
        "topics": [{"slug": t.slug, "name": t.name} for t in topics],
        "brands": [{"slug": b.slug, "name": b.name} for b in brands],
        "intents": [{"slug": i.slug, "name": i.name} for i in intents],
        "genders": [{"slug": g.slug, "name": g.name} for g in genders],
        "price_tiers": [{"slug": p.slug, "name": p.name} for p in price_tiers],
        "origins": [{"slug": o, "name": o} for o in origins]
    })


@bp.route("/stats", methods=["GET"])
def get_stats():
    """Retrieve aggregate statistics for the summary bar."""
    total = db.session.query(func.count(Content.id)).scalar()
    published = db.session.query(func.count(Content.id)).filter(Content.is_published == True).scalar()
    drafts = total - published
    failed = db.session.query(func.count(Article.id)).filter(Article.status == "failed").scalar()
    
    no_topics = db.session.query(func.count(Content.id)).filter(~Content.topics.any()).scalar()
    no_brands = db.session.query(func.count(Content.id)).filter(~Content.brands.any()).scalar()

    return jsonify({
        "total": total,
        "published": published,
        "drafts": drafts,
        "failed": failed,
        "no_topics": no_topics,
        "no_brands": no_brands
    })


@bp.route("/dashboard", methods=["GET"])
def content_dashboard():
    """Render the high-level content analytics dashboard."""
    # Compute distribution metrics
    type_counts = db.session.execute(select(Content.object_type, func.count(Content.id)).group_by(Content.object_type)).all()
    origin_counts = db.session.execute(select(Content.ingestion_origin, func.count(Content.id)).group_by(Content.ingestion_origin)).all()
    status_counts = db.session.execute(select(Article.status, func.count(Article.id)).group_by(Article.status)).all()
    
    # KPIs
    total = db.session.query(func.count(Content.id)).scalar() or 0
    published = db.session.query(func.count(Content.id)).filter(Content.is_published == True).scalar() or 0
    failed = db.session.query(func.count(Article.id)).filter(Article.status == "failed").scalar() or 0
    scraped = db.session.query(func.count(Article.id)).filter(Article.is_content_scraped == True).scalar() or 0
    total_articles = db.session.query(func.count(Article.id)).scalar() or 1
    scrape_coverage = (scraped / total_articles) * 100
    
    # Unclassified (no topics and no brands)
    no_tax = db.session.query(func.count(Content.id)).filter(~Content.topics.any(), ~Content.brands.any()).scalar() or 0

    # Origin Analytics
    origin_analytics = db.session.query(
        Content.ingestion_origin,
        func.count(Content.id).label("count"),
        func.avg(Article.quality_score).label("avg_quality"),
        func.avg(Article.word_count).label("avg_words"),
        func.avg(Content.view_count).label("avg_views")
    ).outerjoin(Article, Content.object_id == Article.id).group_by(Content.ingestion_origin).all()

    origin_table = []
    for row in origin_analytics:
        origin_table.append({
            "origin": row[0] or "Unknown",
            "count": row[1] or 0,
            "avg_quality": round(row[2], 1) if row[2] else 0,
            "avg_words": int(row[3]) if row[3] else 0,
            "avg_views": int(row[4]) if row[4] else 0
        })
        
    # Freshness Distribution
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    d30 = now - timedelta(days=30)
    d90 = now - timedelta(days=90)
    
    freshness_counts = db.session.query(Content.published_at).filter(Content.published_at != None).all()
    freshness_dist = {"< 30 Days": 0, "30-90 Days": 0, "> 90 Days": 0}
    for (pub_at,) in freshness_counts:
        # handle naive vs timezone aware
        if pub_at.tzinfo is None:
            pub_at = pub_at.replace(tzinfo=timezone.utc)
        if pub_at > d30:
            freshness_dist["< 30 Days"] += 1
        elif pub_at > d90:
            freshness_dist["30-90 Days"] += 1
        else:
            freshness_dist["> 90 Days"] += 1
            
    # Source Authority Distribution
    authority_dist = {"High (67-100)": 0, "Medium (34-66)": 0, "Low (0-33)": 0}
    source_scores = db.session.query(Source.authority_score, func.count(Content.id)).join(Content, Content.source_id == Source.id).group_by(Source.authority_score).all()
    for score, count in source_scores:
        s = score or 0
        if s >= 67: authority_dist["High (67-100)"] += count
        elif s >= 34: authority_dist["Medium (34-66)"] += count
        else: authority_dist["Low (0-33)"] += count

    stats = {
        "kpi": {
            "total": total,
            "published": published,
            "drafts": total - published,
            "failed": failed,
            "no_tax": no_tax,
            "scrape_coverage": round(scrape_coverage, 1)
        },
        "type_dist": {row[0]: row[1] for row in type_counts},
        "origin_dist": {row[0] or 'Unknown': row[1] for row in origin_counts},
        "status_dist": {row[0] or 'Pending': row[1] for row in status_counts},
        "freshness_dist": freshness_dist,
        "authority_dist": authority_dist,
        "origin_table": origin_table
    }
    
    return render_template("admin/content_library/dashboard.html", stats=stats)


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


def build_content_inspect_data(id):
    """Return dictionary of data needed for the content inspect/detail view."""
    from app.domains.user.models import User

    content = db.session.scalar(
        select(Content).options(
            joinedload(Content.category),
            joinedload(Content.section),
            joinedload(Content.source),
            joinedload(Content.gender),
            joinedload(Content.intent),
            joinedload(Content.price_tier),
            selectinload(Content.brands),
            selectinload(Content.topics),
            selectinload(Content.linked_items),
            selectinload(Content.comments).joinedload(Comment.user)
        ).where(Content.id == id)
    )
    if not content:
        return None

    target = None
    if content.object_type in ("article", "video", "post"):
        model = {"article": Article, "video": Video, "post": Post}.get(content.object_type)
        if model:
            stmt = select(model).where(model.id == content.object_id)
            if model == Article:
                stmt = stmt.options(selectinload(Article.article_sources).joinedload(ArticleSource.source))
            target = db.session.scalar(stmt)

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
    # Get article status distribution by origin
    origins = db.session.execute(select(Content.ingestion_origin).distinct()).scalars().all()
    stats = []
    
    for origin in origins:
        if not origin: continue
        
        counts = db.session.execute(
            select(Article.status, func.count(Article.id))
            .join(Content, Content.object_id == Article.id)
            .where(Content.object_type == "article")
            .where(Content.ingestion_origin == origin)
            .group_by(Article.status)
        ).all()
        
        status_map = {status: count for status, count in counts}
        total = sum(status_map.values())
        if total > 0:
            stats.append({
                "origin": origin,
                "pending": status_map.get("pending", 0),
                "enriching": status_map.get("enriching", 0),
                "failed": status_map.get("failed", 0),
                "complete": status_map.get("complete", 0),
                "total": total
            })
            
    return jsonify({"stats": stats})

@bp.route("/pipeline/retry", methods=["POST"])
@admin_required
def pipeline_retry():
    data = request.get_json() or {}
    origin = data.get("origin")
    
    query = db.session.query(Article).join(Content, Content.object_id == Article.id).filter(
        Content.object_type == "article",
        Article.status == "failed"
    )
    if origin:
        query = query.filter(Content.ingestion_origin == origin)
        
    articles_to_retry = query.all()
    for a in articles_to_retry:
        a.status = "pending"
        
    db.session.commit()
    return jsonify({"success": True, "retried": len(articles_to_retry)})

# ─────────────────────────────────────────────
# DEDUPLICATION WORKBENCH
# ─────────────────────────────────────────────

@bp.route("/deduplication", methods=["GET"])
@admin_required
def deduplication_view():
    # Find titles with > 1 occurrence
    dup_titles = db.session.execute(
        select(Content.title, func.count(Content.id))
        .group_by(Content.title)
        .having(func.count(Content.id) > 1)
        .order_by(func.count(Content.id).desc())
        .limit(20)
    ).all()
    
    groups = []
    for title, count in dup_titles:
        if not title: continue
        items = db.session.execute(select(Content).where(Content.title == title)).scalars().all()
        groups.append({
            "title": title,
            "count": count,
            "content_list": [{"id": i.id, "type": i.object_type, "published_at": i.published_at.isoformat() if i.published_at else None, "source": i.source.name if i.source else "None"} for i in items]
        })
        
    return render_template("admin/content_library/deduplication.html", duplicate_groups=groups)
