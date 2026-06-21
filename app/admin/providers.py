# app/admin/providers.py
"""
Admin provider management endpoints (sources and stores).

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- N+1 loops replaced with aggregate subqueries for content/item counts and
  latest activity per provider (R-04).
- All queries use modern select() style (R-07).
- Shared pagination helpers from app.admin.helpers (R-18, R-21).
- Extracted _fetch_sources_page() and _fetch_stores_page() helpers to
  eliminate duplication between JSON listing and HTML partial endpoints.
"""
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.taxonomy.models import Source
from app.domains.content.models import Content
from app.domains.item.models import Store, Item, ItemVariant, ItemStoreLink
from app.domains.external.models import LastAPIFetch
from app.domains.interaction.models import View, ItemClick
from app.admin.helpers import parse_pagination_params, make_rows_response
from sqlalchemy import select, func, or_

bp = Blueprint("api_provider", __name__, url_prefix="/admin/providers")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all provider endpoints require admin privilege."""
    pass


# ─────────────────────────────────────────────
# SOURCES (content providers)
# ─────────────────────────────────────────────

def _fetch_sources_page(page, per_page, search):
    """
    Run the paginated sources query with all aggregate subqueries.
    Returns (pagination, serialized_list).
    Shared between list_sources (JSON) and sources_rows (HTML partial).
    """
    stmt = select(Source)
    if search:
        term = f"%{search}%"
        stmt = stmt.where(or_(
            Source.name.ilike(term),
            Source.slug.ilike(term),
            Source.domain.ilike(term),
            Source.id.in_(
                select(Content.source_id)
                .where(Content.ingestion_origin.ilike(term))
            )
        ))
    stmt = stmt.order_by(Source.authority_score.desc(), Source.name.asc())
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    page_source_ids = [s.id for s in pagination.items]

    if page_source_ids:
        content_agg = db.session.execute(
            select(
                Content.source_id,
                func.count(Content.id).label("content_count"),
                func.max(Content.ingested_at).label("latest_ingested_at"),
                func.sum(
                    Content.view_count + Content.like_count + Content.dislike_count
                    + Content.save_count + Content.comment_count
                ).label("engagement")
            )
            .where(Content.source_id.in_(page_source_ids))
            .group_by(Content.source_id)
        ).all()
        content_agg_map = {r.source_id: r for r in content_agg}

        page_source_slugs = [s.slug for s in pagination.items]
        fetch_agg = db.session.execute(
            select(
                LastAPIFetch.source,
                func.max(LastAPIFetch.last_fetched_at).label("last_crawl"),
                func.sum(LastAPIFetch.success_count).label("success_count"),
                func.sum(LastAPIFetch.failure_count).label("failure_count"),
                func.max(LastAPIFetch.consecutive_failures).label("consecutive_failures")
            )
            .where(func.lower(LastAPIFetch.source).in_([sl.lower() for sl in page_source_slugs]))
            .group_by(LastAPIFetch.source)
        ).all()
        fetch_agg_map = {r.source.lower(): r for r in fetch_agg}

        channels_rows = db.session.execute(
            select(Content.source_id, Content.ingestion_origin)
            .where(Content.source_id.in_(page_source_ids))
            .where(Content.ingestion_origin.is_not(None))
            .distinct()
        ).all()
        channels_map = {}
        for r in channels_rows:
            channels_map.setdefault(r.source_id, []).append(r.ingestion_origin)
    else:
        content_agg_map, fetch_agg_map, channels_map = {}, {}, {}

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    serialized = []
    for s in pagination.items:
        agg             = content_agg_map.get(s.id)
        content_count   = agg.content_count if agg else 0
        latest_activity = agg.latest_ingested_at.isoformat() if agg and agg.latest_ingested_at else None
        engagement      = int(agg.engagement) if agg and agg.engagement is not None else 0
        
        freshness_days = None
        if agg and agg.latest_ingested_at:
            latest = agg.latest_ingested_at
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            freshness_days = (now - latest).days

        fetch_info      = fetch_agg_map.get(s.slug.lower())
        last_crawl      = fetch_info.last_crawl.isoformat() if fetch_info and fetch_info.last_crawl else None
        success_count   = fetch_info.success_count if (fetch_info and fetch_info.success_count is not None) else 0
        failure_count   = fetch_info.failure_count if (fetch_info and fetch_info.failure_count is not None) else 0
        consec_failures = fetch_info.consecutive_failures if (fetch_info and fetch_info.consecutive_failures is not None) else 0
        total_fetches   = success_count + failure_count
        success_rate    = round((success_count / total_fetches) * 100.0, 1) if total_fetches > 0 else 100.0
        
        if not s.is_active:
            status_val = "failed"
        elif content_count == 0 or success_rate < 80.0:
            status_val = "warning"
        else:
            status_val = "healthy"
            
        tier = 1 if s.authority_score >= 80 else (2 if s.authority_score >= 50 else 3)
        channels = channels_map.get(s.id, [])
        
        serialized.append({
            "id":              s.id,
            "logo-url":        s.logo_url,
            "link":            {'url': f'https://{s.domain}', 'name': s.name},
            "tier":            tier,
            "channels":        channels,
            "freshness":       freshness_days,
            "content-count":   content_count,
            "success-rate":    success_rate,
            "failures":        consec_failures,
            "status":          status_val,
            "slug":            s.slug,
        })
    return pagination, serialized


@bp.route("/sources", methods=["GET"])
def list_sources():
    """Paginated listing of sources/content providers with counts and latest content."""
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    pagination, serialized = _fetch_sources_page(page, per_page, search)
    return jsonify({
        "sources":  serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/sources/health_stats", methods=["GET"])
def get_source_health_stats():
    """Return fast KPI stats for the sources health dashboard."""
    from datetime import datetime, timezone, timedelta
    
    now = datetime.now(timezone.utc)
    
    sources = db.session.execute(select(Source.id, Source.slug, Source.is_active)).all()
    
    content_agg = db.session.execute(
        select(Content.source_id, func.count(Content.id), func.max(Content.ingested_at))
        .group_by(Content.source_id)
    ).all()
    content_map = {r[0]: {"count": r[1], "latest": r[2]} for r in content_agg}
    
    fetch_agg = db.session.execute(
        select(func.lower(LastAPIFetch.source), func.sum(LastAPIFetch.success_count), func.sum(LastAPIFetch.failure_count))
        .group_by(func.lower(LastAPIFetch.source))
    ).all()
    fetch_map = {r[0]: {"success": r[1] or 0, "failure": r[2] or 0} for r in fetch_agg}
    
    healthy = 0
    warning = 0
    failed = 0
    silent = 0
    
    for s_id, s_slug, is_active in sources:
        if not is_active:
            failed += 1
            continue
            
        c_stats = content_map.get(s_id, {"count": 0, "latest": None})
        f_stats = fetch_map.get(s_slug.lower(), {"success": 0, "failure": 0})
        
        c_count = c_stats["count"]
        latest = c_stats["latest"]
        
        if latest:
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            if (now - latest) > timedelta(days=7):
                silent += 1
            
        success = f_stats["success"]
        failure = f_stats["failure"]
        total_fetches = success + failure
        success_rate = (success / total_fetches * 100.0) if total_fetches > 0 else 100.0
        
        if c_count == 0 or success_rate < 80.0:
            warning += 1
        else:
            healthy += 1
            
    return jsonify({
        "total": len(sources),
        "active": len(sources) - failed,
        "healthy": healthy,
        "warning": warning,
        "failed": failed,
        "silent": silent
    })


# ─────────────────────────────────────────────
# STORES (product / affiliate providers)
# ─────────────────────────────────────────────

def _fetch_stores_page(page, per_page, search):
    """
    Run the paginated stores query with all aggregate subqueries.
    Returns (pagination, serialized_list).
    Shared between list_stores (JSON) and stores_rows (HTML partial).
    """
    stmt = select(Store)
    if search:
        term = f"%{search}%"
        stmt = stmt.where(or_(
            Store.name.ilike(term),
            Store.slug.ilike(term),
            Store.website.ilike(term),
        ))
    stmt = stmt.order_by(Store.name.asc())
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    page_store_ids = [st.id for st in pagination.items]

    if page_store_ids:
        product_count_rows = db.session.execute(
            select(
                ItemStoreLink.store_id,
                func.count(func.distinct(ItemVariant.item_id)).label("product_count"),
            )
            .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .group_by(ItemStoreLink.store_id)
        ).all()
        product_count_map = {r.store_id: r.product_count for r in product_count_rows}

        clicks_rows = db.session.execute(
            select(ItemStoreLink.store_id, func.count(ItemClick.id).label("clicks"))
            .join(ItemClick, ItemClick.item_store_link_id == ItemStoreLink.id)
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .group_by(ItemStoreLink.store_id)
        ).all()
        clicks_map = {r.store_id: r.clicks for r in clicks_rows}

        views_rows_q = db.session.execute(
            select(ItemStoreLink.store_id, func.count(View.id).label("views"))
            .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
            .join(View, (View.target_id == ItemVariant.item_id) & (View.target_type == 'item'))
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .group_by(ItemStoreLink.store_id)
        ).all()
        views_map = {r.store_id: r.views for r in views_rows_q}

        latest_activity_rows = db.session.execute(
            select(
                ItemStoreLink.store_id,
                func.max(Item.created_at).label("latest_created_at"),
            )
            .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
            .join(Item, Item.id == ItemVariant.item_id)
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .group_by(ItemStoreLink.store_id)
        ).all()
        latest_activity_map = {r.store_id: r.latest_created_at for r in latest_activity_rows}
    else:
        product_count_map, clicks_map, views_map, latest_activity_map = {}, {}, {}, {}

    serialized = []
    for st in pagination.items:
        product_count   = product_count_map.get(st.id, 0)
        latest_activity = latest_activity_map.get(st.id)
        clicks          = clicks_map.get(st.id, 0)
        views           = views_map.get(st.id, 0)
        ctr             = round((clicks / views) * 100.0, 2) if views > 0 else 0.0
        if not st.is_active:
            status_val = "failed"
        elif product_count == 0:
            status_val = "warning"
        else:
            status_val = "healthy"
        serialized.append({
            "id":                  st.id,
            "link":                {'url': st.website, 'name': st.name},
            "affiliate-network": st.affiliate_network,
            "product-count":     product_count,
            "clicks":            clicks,
            "ctr":               ctr,
            "conversions":       0,
            "status":            status_val,
            "slug":              st.slug,
        })
    return pagination, serialized


@bp.route("/stores", methods=["GET"])
def list_stores():
    """Paginated listing of stores/commercial providers with counts and latest products."""
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    pagination, serialized = _fetch_stores_page(page, per_page, search)
    return jsonify({
        "stores":   serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })


@bp.route("/stores/health_stats", methods=["GET"])
def get_store_health_stats():
    """Return fast KPI stats for the stores/sync health dashboard."""
    from datetime import datetime, timezone, timedelta
    from app.domains.item.models import ItemStoreLink
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    
    total_links = db.session.scalar(select(func.count(ItemStoreLink.id))) or 0
    active_links = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.is_active == True)) or 0
    
    synced_today = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.last_synced_at >= today_start)
    ) or 0
    
    synced_this_week = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.last_synced_at >= week_start)
    ) or 0
    
    never_synced = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.last_synced_at.is_(None))
    ) or 0
    
    out_of_stock = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.availability == 'OutOfStock')
    ) or 0
    
    # Top stores by out of stock count
    oos_stores_rows = db.session.execute(
        select(Store.name, func.count(ItemStoreLink.id))
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
        .where(ItemStoreLink.availability == 'OutOfStock')
        .group_by(Store.name)
        .order_by(func.count(ItemStoreLink.id).desc())
        .limit(5)
    ).all()
    
    oos_by_store = [{"name": r[0], "count": r[1]} for r in oos_stores_rows]
    
    return jsonify({
        "total_links": total_links,
        "active_links": active_links,
        "synced_today": synced_today,
        "synced_this_week": synced_this_week,
        "never_synced": never_synced,
        "out_of_stock": out_of_stock,
        "oos_by_store": oos_by_store
    })


@bp.route("/stores/coverage_stats", methods=["GET"])
def get_store_coverage_stats():
    """Return affiliate coverage and commission stats."""
    from app.domains.item.models import ItemStoreLink, ItemVariant
    from app.domains.item.models import Item
    
    # 1. Category Coverage per Store
    # How many distinct categories each store covers
    coverage_rows = db.session.execute(
        select(Store.name, func.count(func.distinct(Item.category_id)))
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
        .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
        .join(Item, Item.id == ItemVariant.item_id)
        .group_by(Store.name)
        .order_by(func.count(func.distinct(Item.category_id)).desc())
    ).all()
    
    category_coverage = [{"name": r[0], "count": r[1]} for r in coverage_rows]
    
    # 2. Commission Rate Distribution
    # Average commission rate per store
    commission_rows = db.session.execute(
        select(Store.name, func.avg(ItemStoreLink.commission_rate))
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
        .where(ItemStoreLink.commission_rate != None)
        .group_by(Store.name)
        .order_by(func.avg(ItemStoreLink.commission_rate).desc())
    ).all()
    
    commission_rates = [{"name": r[0], "avg_rate": round(float(r[1]), 2)} for r in commission_rows]
    
    return jsonify({
        "category_coverage": category_coverage,
        "commission_rates": commission_rates
    })

@bp.route("/sources/rows", methods=["GET"])
def sources_rows():
    """Return server-rendered HTML rows partial for sources AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    pagination, serialized = _fetch_sources_page(page, per_page, search)
    html = render_template("admin/components/_rows.html", items=serialized, domain_type="source", domain_target_type="contents")
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


@bp.route("/stores/rows", methods=["GET"])
def stores_rows():
    """Return server-rendered HTML rows partial for stores AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    pagination, serialized = _fetch_stores_page(page, per_page, search)
    html = render_template("admin/components/_rows.html", items=serialized, domain_type="store", domain_target_type="items")
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


# ─────────────────────────────────────────────
# INSPECT ENDPOINTS
# ─────────────────────────────────────────────

def build_source_inspect_data(id):
    source = db.session.get(Source, id)
    if not source:
        return None
        
    content_count = db.session.scalar(select(func.count(Content.id)).filter(Content.source_id == id)) or 0
    from app.admin.helpers import format_status
    from app.admin.tables import get_inspect_table
    from app.domains.content.models import Article
    from app.domains.taxonomy.models import Category
    from app.domains.relationships import ArticleSource
    
    analytics = db.session.query(
        func.avg(Article.quality_score),
        func.avg(Article.word_count),
        func.count(Article.id).filter(Article.is_content_scraped == True),
        func.min(Content.published_at),
        func.max(Content.published_at)
    ).select_from(Content).join(Article, Content.object_id == Article.id).filter(Content.source_id == id, Content.object_type == 'article').first()
    
    avg_quality = round(analytics[0], 1) if analytics and analytics[0] else 0
    avg_words = int(analytics[1]) if analytics and analytics[1] else 0
    scraped_count = analytics[2] if analytics and analytics[2] else 0
    scrape_cov = round((scraped_count / content_count * 100), 1) if content_count > 0 else 0
    date_min = analytics[3].strftime('%Y-%m-%d') if analytics and analytics[3] else "—"
    date_max = analytics[4].strftime('%Y-%m-%d') if analytics and analytics[4] else "—"
    
    # 1. Content type breakdown
    type_counts = db.session.execute(
        select(Content.object_type, func.count(Content.id))
        .where(Content.source_id == id)
        .group_by(Content.object_type)
    ).all()
    type_breakdown = {r[0]: r[1] for r in type_counts}
    
    # 2. Ingestion Channels breakdown
    channel_counts = db.session.execute(
        select(Content.ingestion_origin, func.count(Content.id))
        .where(Content.source_id == id)
        .where(Content.ingestion_origin.is_not(None))
        .group_by(Content.ingestion_origin)
    ).all()
    channels = [r[0] for r in channel_counts]
    
    # 3. Category coverage
    category_counts = db.session.scalar(
        select(func.count(func.distinct(Content.category_id)))
        .where(Content.source_id == id)
    ) or 0
    
    # 4. Article pipeline status
    status_counts = db.session.execute(
        select(Article.status, func.count(Article.id))
        .join(Content, Content.object_id == Article.id)
        .where(Content.source_id == id)
        .where(Content.object_type == 'article')
        .group_by(Article.status)
    ).all()
    pipeline_status = {r[0]: r[1] for r in status_counts}
    
    # 5. Engagement breakdown
    eng_stats = db.session.execute(
        select(
            func.sum(Content.view_count).label("views"),
            func.sum(Content.like_count).label("likes"),
            func.sum(Content.save_count).label("saves"),
            func.sum(Content.comment_count).label("comments")
        ).where(Content.source_id == id)
    ).first()
    
    # 6. Fetch health
    fetch_health = db.session.execute(
        select(
            func.sum(LastAPIFetch.success_count).label("success"),
            func.sum(LastAPIFetch.failure_count).label("failures"),
            func.max(LastAPIFetch.consecutive_failures).label("consecutive"),
            func.max(LastAPIFetch.last_fetched_at).label("last_fetch")
        )
        .where(func.lower(LastAPIFetch.source) == source.slug.lower())
    ).first()
    
    # 7. Multi-source attribution stats
    primary_count = db.session.scalar(
        select(func.count(Article.id))
        .where(Article.primary_source_id != None)
        .join(ArticleSource, Article.primary_source_id == ArticleSource.id)
        .where(ArticleSource.source_id == id)
    ) or 0
    secondary_count = db.session.scalar(
        select(func.count(ArticleSource.id))
        .where(ArticleSource.source_id == id)
    ) or 0
    secondary_count = max(0, secondary_count - primary_count)
    
    # 8. Top articles
    top_articles = db.session.execute(
        select(Content.id, Content.title, Content.view_count)
        .where(Content.source_id == id)
        .where(Content.object_type == 'article')
        .order_by(Content.view_count.desc())
        .limit(5)
    ).all()
    top_articles_data = [{"id": r[0], "title": r[1] or "Untitled", "views": r[2]} for r in top_articles]
    
    data = {
        "id": f"#{source.id}",
        "name": source.name,
        "slug": source.slug,
        "domain": source.domain,
        "status": format_status(source.is_active),
        "authority score": str(source.authority_score),
        "avg quality score": str(avg_quality),
        "avg word count": str(avg_words),
        "scrape coverage": f"{scrape_cov}%",
        "published date range": f"{date_min} to {date_max}",
        
        "channels": ", ".join(channels) if channels else "None",
        "last fetch": fetch_health.last_fetch.strftime('%Y-%m-%d %H:%M') if fetch_health and fetch_health.last_fetch else "—",
        "success count": str(fetch_health.success or 0),
        "failure count": str(fetch_health.failures or 0),
        "consecutive failures": str(fetch_health.consecutive or 0),
        
        "article count": str(type_breakdown.get('article', 0)),
        "video count": str(type_breakdown.get('video', 0)),
        "post count": str(type_breakdown.get('post', 0)),
        "categories covered": str(category_counts),
        
        "pending": str(pipeline_status.get('pending', 0)),
        "enriching": str(pipeline_status.get('enriching', 0)),
        "complete": str(pipeline_status.get('complete', 0)),
        "failed": str(pipeline_status.get('failed', 0)),
        
        "total views": str(eng_stats.views or 0) if eng_stats else "0",
        "total likes": str(eng_stats.likes or 0) if eng_stats else "0",
        "total saves": str(eng_stats.saves or 0) if eng_stats else "0",
        "total comments": str(eng_stats.comments or 0) if eng_stats else "0",
        
        "primary attribution count": str(primary_count),
        "secondary attribution count": str(secondary_count)
    }
    inspect_table = get_inspect_table("sources", data)
    return {
        "inspect_table": inspect_table,
        "inspect_id": source.id,
        "source": source,
        "top_articles": top_articles_data
    }


def build_store_inspect_data(id):
    store = db.session.get(Store, id)
    if not store:
        return None
        
    product_count = db.session.scalar(
        select(func.count(func.distinct(ItemVariant.item_id)))
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
        .where(ItemStoreLink.store_id == id)
    ) or 0
    
    from app.admin.helpers import format_status
    from app.admin.tables import get_inspect_table
    
    data = {
        "id": f"#{store.id}",
        "name": store.name,
        "slug": store.slug,
        "website": store.website,
        "status": format_status(store.is_active),
        "affiliate network": store.affiliate_network or "—",
        "product count": str(product_count),
        "country": store.country or "—",
        "currency": store.currency or "—",
        "api enabled": "Yes" if store.api_enabled else "No",
    }
    inspect_table = get_inspect_table("stores", data)
    return {
        "inspect_table": inspect_table,
        "inspect_id": store.id
    }


@bp.route("/sources/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_source(id):
    data = build_source_inspect_data(id)
    if not data:
        return "<p class='text-muted'>Source not found.</p>", 404
    return render_template("admin/components/_inspect.html", **data)


@bp.route("/stores/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_store(id):
    data = build_store_inspect_data(id)
    if not data:
        return "<p class='text-muted'>Store not found.</p>", 404
    return render_template("admin/components/_inspect.html", **data)


@bp.route("/sources/quality-data", methods=["GET"])
def get_sources_quality_data():
    from app.domains.content.models import Article
    from app.domains.external.models import APIUsage
    from datetime import datetime, timezone
    from sqlalchemy import cast, Date

    now = datetime.now(timezone.utc)

    # 1. Quality Tier Leaderboard & Scrape Coverage Leaderboard & Word Count & Freshness
    rows = db.session.execute(
        select(
            Source.name,
            func.avg(Article.quality_score).label("avg_quality"),
            func.count(Article.id).label("total_articles"),
            func.sum(cast(Article.is_content_scraped, db.Integer)).label("scraped_articles"),
            func.avg(Article.word_count).label("avg_words"),
            func.max(Content.ingested_at).label("latest_ingested")
        )
        .join(Content, Content.source_id == Source.id)
        .join(Article, Article.id == Content.object_id)
        .where(Content.object_type == 'article')
        .group_by(Source.name)
    ).all()

    quality_leaderboard = []
    scrape_leaderboard = []
    word_counts = []
    freshness_index = []

    for name, avg_q, total_art, scraped_art, avg_w, latest_ingest in rows:
        # Quality
        q_score = round(avg_q, 1) if avg_q else 0
        if q_score >= 70:
            tier = "High"
        elif q_score >= 40:
            tier = "Medium"
        else:
            tier = "Low"
        quality_leaderboard.append({"source": name, "avg_quality": q_score, "tier": tier})

        # Scrape Coverage
        total = total_art or 0
        scraped = scraped_art or 0
        scrape_pct = round((scraped / total * 100), 1) if total > 0 else 0
        if scrape_pct >= 90:
            health = "Healthy"
        elif scrape_pct >= 50:
            health = "Warning"
        else:
            health = "Critical"
        scrape_leaderboard.append({"source": name, "scrape_pct": scrape_pct, "health": health})

        # Word count
        words = int(avg_w) if avg_w else 0
        word_counts.append({"source": name, "avg_words": words})

        # Freshness
        if latest_ingest:
            latest = latest_ingest
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            days_stale = (now - latest).days
            if days_stale > 30:
                severity = "Critical"
            elif days_stale > 7:
                severity = "Warning"
            else:
                severity = "Healthy"
            freshness_index.append({
                "source": name,
                "latest_ingested": latest.strftime('%Y-%m-%d %H:%M'),
                "days_stale": days_stale,
                "severity": severity
            })

    quality_leaderboard.sort(key=lambda x: x["avg_quality"], reverse=True)
    scrape_leaderboard.sort(key=lambda x: x["scrape_pct"], reverse=True)
    word_counts.sort(key=lambda x: x["avg_words"], reverse=True)
    freshness_index.sort(key=lambda x: x["days_stale"], reverse=True)

    word_count_data = {
        "labels": [w["source"] for w in word_counts[:15]],
        "data": [w["avg_words"] for w in word_counts[:15]]
    }

    # 5. Ingestion Yield Rate Tracking
    yield_data = {"labels": [], "datasets": []}
    
    usage_rows = db.session.execute(
        select(APIUsage.api_name, APIUsage.date, func.sum(APIUsage.request_count))
        .group_by(APIUsage.api_name, APIUsage.date)
        .order_by(APIUsage.date)
    ).all()
    
    content_rows = db.session.execute(
        select(Content.ingestion_origin, cast(Content.ingested_at, Date), func.count(Content.id))
        .group_by(Content.ingestion_origin, cast(Content.ingested_at, Date))
        .order_by(cast(Content.ingested_at, Date))
    ).all()

    usage_map = {}
    for api_name, date_val, req_count in usage_rows:
        if api_name not in usage_map:
            usage_map[api_name] = {}
        usage_map[api_name][str(date_val)] = req_count

    content_map = {}
    for origin, date_val, count in content_rows:
        if not origin: continue
        if origin not in content_map:
            content_map[origin] = {}
        content_map[origin][str(date_val)] = count

    all_dates = set()
    for o, dates in usage_map.items():
        all_dates.update(dates.keys())
    for o, dates in content_map.items():
        all_dates.update(dates.keys())
    all_dates = sorted(list(all_dates))[-14:]

    channels = set(usage_map.keys()) | set(content_map.keys())
    
    for channel in channels:
        ds_data = []
        for d in all_dates:
            reqs = usage_map.get(channel, {}).get(d, 0)
            arts = content_map.get(channel, {}).get(d, 0)
            if reqs > 0:
                ds_data.append(round(arts / reqs, 2))
            elif arts > 0:
                ds_data.append(arts)
            else:
                ds_data.append(0)
        yield_data["datasets"].append({
            "label": channel,
            "data": ds_data
        })
    yield_data["labels"] = all_dates

    return jsonify({
        "quality_leaderboard": quality_leaderboard[:15],
        "scrape_leaderboard": scrape_leaderboard[:15],
        "word_counts": word_count_data,
        "freshness_index": freshness_index[:15],
        "yield_rate": yield_data
    })

