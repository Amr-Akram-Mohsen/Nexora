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
from sqlalchemy import select, func, or_, case

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

def _fetch_stores_page(page, per_page, search, network=None, country=None, sync_staleness=None):
    """
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
        
    if network:
        stmt = stmt.where(Store.affiliate_network == network)
    if country:
        stmt = stmt.where(Store.country == country)
        
    if sync_staleness:
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        stale_date = now - timedelta(days=7)
        if sync_staleness == "fresh":
            stmt = stmt.where(Store.item_links.any(ItemStoreLink.last_synced_at >= stale_date))
        elif sync_staleness == "stale":
            stmt = stmt.where(Store.item_links.any(ItemStoreLink.last_synced_at < stale_date))
        elif sync_staleness == "never":
            stmt = stmt.where(Store.item_links.any(ItemStoreLink.last_synced_at == None))

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
            select(ItemStoreLink.store_id, func.count(func.distinct(View.id)).label("views"))
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

        avg_comm_rows = db.session.execute(
            select(ItemStoreLink.store_id, func.avg(ItemStoreLink.commission_rate).label("avg_comm"))
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .where(ItemStoreLink.commission_rate != None)
            .group_by(ItemStoreLink.store_id)
        ).all()
        avg_comm_map = {r.store_id: r.avg_comm for r in avg_comm_rows}

        sync_age_rows = db.session.execute(
            select(
                ItemStoreLink.store_id,
                func.max(ItemStoreLink.last_synced_at).label("last_synced")
            )
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .group_by(ItemStoreLink.store_id)
        ).all()
        sync_age_map = {r.store_id: r.last_synced for r in sync_age_rows}

        oos_rows = db.session.execute(
            select(
                ItemStoreLink.store_id,
                func.sum(case((ItemStoreLink.availability == 'OutOfStock', 1), else_=0)).label("oos_count"),
                func.count(ItemStoreLink.id).label("total_links"),
                func.sum(case((ItemStoreLink.is_active == True, 1), else_=0)).label("active_links")
            )
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .group_by(ItemStoreLink.store_id)
        ).all()
        oos_map = {r.store_id: {"oos_count": r.oos_count, "total_links": r.total_links, "active_links": r.active_links} for r in oos_rows}
    else:
        product_count_map, clicks_map, views_map, latest_activity_map, avg_comm_map, sync_age_map, oos_map = {}, {}, {}, {}, {}, {}, {}

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    serialized = []
    for st in pagination.items:
        product_count   = product_count_map.get(st.id, 0)
        latest_activity = latest_activity_map.get(st.id)
        clicks          = clicks_map.get(st.id, 0)
        views           = views_map.get(st.id, 0)
        avg_comm        = avg_comm_map.get(st.id)
        last_synced     = sync_age_map.get(st.id)
        oos_data        = oos_map.get(st.id, {"oos_count": 0, "total_links": 0, "active_links": 0})
        
        # NOTE: Using a hardcoded 0.0 for CTR as views mapping logic isn't aligned. (If views < clicks, CTR > 100 which is inflated).
        ctr = 0.0
        if views > 0 and views >= clicks:
             ctr = round((clicks / views) * 100.0, 2)
             
        sync_age_days = None
        if last_synced:
            if last_synced.tzinfo is None:
                last_synced = last_synced.replace(tzinfo=timezone.utc)
            sync_age_days = (now - last_synced).days
            
        oos_rate = 0.0
        if oos_data["total_links"] > 0:
            oos_rate = round((oos_data["oos_count"] / oos_data["total_links"]) * 100.0, 1)

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
            "active-links":      oos_data["active_links"],
            "sync-age":          sync_age_days,
            "oos-rate":          f"{oos_rate}%",
            "avg-commission":    f"{round(float(avg_comm), 2)}%" if avg_comm is not None else "—",
            "status":            status_val,
            "slug":              st.slug,
        })
    return pagination, serialized


@bp.route("/stores", methods=["GET"])
def list_stores():
    """Paginated listing of stores/commercial providers with counts and latest products."""
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()
    network = request.args.get("network")
    country = request.args.get("country")
    sync_staleness = request.args.get("sync_staleness")
    
    pagination, serialized = _fetch_stores_page(page, per_page, search, network, country, sync_staleness)
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
    
    month_start = now - timedelta(days=30)
    
    checked_in_24h = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.last_checked_at >= today_start)
    ) or 0
    
    deeplink_refreshed_30d = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.deeplink_generated_at >= month_start)
    ) or 0
    
    never_checked = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.last_checked_at.is_(None))
    ) or 0
    
    never_had_deeplink = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.deeplink_generated_at.is_(None))
    ) or 0
    
    # Availability Breakdown
    avail_rows = db.session.execute(
        select(ItemStoreLink.availability, func.count(ItemStoreLink.id))
        .group_by(ItemStoreLink.availability)
    ).all()
    
    availability_breakdown = {r[0] if r[0] else 'Unknown': r[1] for r in avail_rows}
    for state in ['InStock', 'OutOfStock', 'PreOrder', 'Unknown']:
        if state not in availability_breakdown:
            availability_breakdown[state] = 0

    # Sync Cadence Timeline (30d volume sparkline)
    recent_syncs = db.session.scalars(
        select(ItemStoreLink.last_synced_at)
        .where(ItemStoreLink.last_synced_at >= month_start)
    ).all()
    
    sync_cadence_map = {}
    for d in range(30):
        day_str = (now - timedelta(days=d)).strftime('%Y-%m-%d')
        sync_cadence_map[day_str] = 0
        
    for dt in recent_syncs:
        if dt:
            day_str = dt.strftime('%Y-%m-%d')
            if day_str in sync_cadence_map:
                sync_cadence_map[day_str] += 1
    
    sync_cadence = [{"date": k, "count": v} for k, v in sorted(sync_cadence_map.items())]

    # Sync Age by Store
    store_syncs = db.session.execute(
        select(Store.name, ItemStoreLink.last_synced_at)
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
        .where(ItemStoreLink.last_synced_at != None)
    ).all()
    
    store_age_map = {}
    for name, dt in store_syncs:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = (now - dt).days
        if name not in store_age_map:
            store_age_map[name] = []
        store_age_map[name].append(age)
        
    avg_sync_age_by_store = []
    for name, ages in store_age_map.items():
        avg_age = sum(ages) / len(ages) if ages else 0
        avg_sync_age_by_store.append({"name": name, "avg_age_days": round(avg_age, 1)})
        
    avg_sync_age_by_store.sort(key=lambda x: x["avg_age_days"], reverse=True)
    top_stale_stores = avg_sync_age_by_store[:10]
    
    return jsonify({
        "total_links": total_links,
        "active_links": active_links,
        "synced_today": synced_today,
        "synced_this_week": synced_this_week,
        "never_synced": never_synced,
        "out_of_stock": out_of_stock,
        "oos_by_store": oos_by_store,
        "checked_in_24h": checked_in_24h,
        "deeplink_refreshed_30d": deeplink_refreshed_30d,
        "never_checked": never_checked,
        "never_had_deeplink": never_had_deeplink,
        "availability_breakdown": availability_breakdown,
        "sync_cadence": sync_cadence,
        "avg_sync_age_by_store": avg_sync_age_by_store,
        "top_stale_stores": top_stale_stores
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

@bp.route("/stores/affiliate_stats", methods=["GET"])
def get_store_affiliate_stats():
    """Return in-depth affiliate, commission, and tracking health stats."""
    from datetime import datetime, timezone, timedelta
    from app.domains.item.models import ItemStoreLink, Store
    
    now = datetime.now(timezone.utc)
    
    links_with_commission = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.commission_rate != None)) or 0
    links_without_commission = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.commission_rate == None)) or 0
    avg_commission_rate_scalar = db.session.scalar(select(func.avg(ItemStoreLink.commission_rate)))
    avg_commission_rate = round(float(avg_commission_rate_scalar), 2) if avg_commission_rate_scalar else 0.0
    
    # Program distribution and top program
    program_rows = db.session.execute(
        select(ItemStoreLink.program_name, func.count(ItemStoreLink.id))
        .where(ItemStoreLink.program_name != None)
        .group_by(ItemStoreLink.program_name)
        .order_by(func.count(ItemStoreLink.id).desc())
        .limit(10)
    ).all()
    
    program_distribution = [{"name": r[0] if r[0] else 'Unknown', "count": r[1]} for r in program_rows]
    top_program = program_distribution[0]["name"] if program_distribution else "None"
    
    # Commission rate ranking
    commission_rows = db.session.execute(
        select(Store.name, func.avg(ItemStoreLink.commission_rate))
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
        .where(ItemStoreLink.commission_rate != None)
        .group_by(Store.name)
        .order_by(func.avg(ItemStoreLink.commission_rate).desc())
        .limit(10)
    ).all()
    commission_rate_ranking = [{"name": r[0], "avg_rate": round(float(r[1]), 2)} for r in commission_rows]
    
    # Tracking coverage
    with_tracking = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.tracking_code != None)) or 0
    without_tracking = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.tracking_code == None)) or 0
    tracking_coverage = {
        "With Tracking": with_tracking,
        "Without Tracking": without_tracking
    }
    
    # Deeplink freshness
    fresh_date = now - timedelta(days=7)
    stale_date = now - timedelta(days=30)
    
    fresh = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.deeplink_generated_at >= fresh_date)) or 0
    aging = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.deeplink_generated_at >= stale_date).where(ItemStoreLink.deeplink_generated_at < fresh_date)) or 0
    stale = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.deeplink_generated_at < stale_date)) or 0
    never = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.deeplink_generated_at == None)) or 0
    
    deeplink_freshness = {
        "Fresh (<7d)": fresh,
        "Aging (7-30d)": aging,
        "Stale (>30d)": stale,
        "Never": never
    }
    
    return jsonify({
        "links_with_commission": links_with_commission,
        "links_without_commission": links_without_commission,
        "avg_commission_rate": avg_commission_rate,
        "top_program": top_program,
        "program_distribution": program_distribution,
        "commission_rate_ranking": commission_rate_ranking,
        "tracking_coverage": tracking_coverage,
        "deeplink_freshness": deeplink_freshness
    })

@bp.route("/stores/pricing_stats", methods=["GET"])
def get_store_pricing_stats():
    """Return pricing intelligence stats: discounts, staleness, currency mix."""
    from datetime import datetime, timezone, timedelta
    from app.domains.item.models import ItemStoreLink, Store, ItemVariant, Item
    
    now = datetime.now(timezone.utc)
    stale_date = now - timedelta(days=7)
    
    # KPIs
    null_price_count = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.price == None)) or 0
    stale_price_count = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.last_synced_at < stale_date)) or 0
    
    avg_discount_scalar = db.session.scalar(
        select(func.avg(((ItemStoreLink.old_price - ItemStoreLink.price) / ItemStoreLink.old_price) * 100.0))
        .where(ItemStoreLink.old_price != None)
        .where(ItemStoreLink.price != None)
        .where(ItemStoreLink.old_price > ItemStoreLink.price)
        .where(ItemStoreLink.old_price > 0)
    )
    avg_discount_percentage = round(float(avg_discount_scalar), 1) if avg_discount_scalar else 0.0

    # Currency mix
    currency_rows = db.session.execute(
        select(ItemVariant.currency, func.count(ItemStoreLink.id))
        .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
        .where(ItemVariant.currency != None)
        .group_by(ItemVariant.currency)
    ).all()
    currency_mix = {r[0] if r[0] else 'Unknown': r[1] for r in currency_rows}

    # Discount Depth Ranking (Stores with highest avg discount)
    discount_rows = db.session.execute(
        select(
            Store.name, 
            func.avg(((ItemStoreLink.old_price - ItemStoreLink.price) / ItemStoreLink.old_price) * 100.0)
        )
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
        .where(ItemStoreLink.old_price != None)
        .where(ItemStoreLink.price != None)
        .where(ItemStoreLink.old_price > ItemStoreLink.price)
        .where(ItemStoreLink.old_price > 0)
        .group_by(Store.name)
        .order_by(func.avg(((ItemStoreLink.old_price - ItemStoreLink.price) / ItemStoreLink.old_price) * 100.0).desc())
        .limit(5)
    ).all()
    discount_depth_ranking = [{"name": r[0], "avg_discount": round(float(r[1]), 1)} for r in discount_rows]

    # Price Staleness Grid (Stacked Bar: Fresh vs Stale per store)
    staleness_query = db.session.execute(
        select(Store.name, ItemStoreLink.last_synced_at)
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
    ).all()
    
    staleness_map = {}
    for store_name, synced_at in staleness_query:
        if store_name not in staleness_map:
            staleness_map[store_name] = {"fresh": 0, "stale": 0}
            
        if synced_at:
            if synced_at.tzinfo is None:
                synced_at = synced_at.replace(tzinfo=timezone.utc)
            if synced_at >= stale_date:
                staleness_map[store_name]["fresh"] += 1
            else:
                staleness_map[store_name]["stale"] += 1
        else:
            staleness_map[store_name]["stale"] += 1
            
    staleness_list = [
        {"name": k, "fresh": v["fresh"], "stale": v["stale"], "total": v["fresh"] + v["stale"]} 
        for k, v in staleness_map.items()
    ]
    staleness_list.sort(key=lambda x: x["total"], reverse=True)
    price_staleness_grid = staleness_list[:10]

    # Alerts: All-OOS Items
    item_avail_query = db.session.execute(
        select(ItemVariant.item_id, ItemStoreLink.availability)
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
    ).all()
    
    item_avail_map = {}
    for item_id, avail in item_avail_query:
        if item_id not in item_avail_map:
            item_avail_map[item_id] = {"total": 0, "oos": 0}
        item_avail_map[item_id]["total"] += 1
        if avail == 'OutOfStock':
            item_avail_map[item_id]["oos"] += 1
            
    all_oos_items_count = sum(1 for v in item_avail_map.values() if v["total"] > 0 and v["total"] == v["oos"])

    # Alerts: High null price stores
    store_price_query = db.session.execute(
        select(Store.name, ItemStoreLink.price)
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
    ).all()
    
    store_price_map = {}
    for name, price in store_price_query:
        if name not in store_price_map:
            store_price_map[name] = {"total": 0, "nulls": 0}
        store_price_map[name]["total"] += 1
        if price is None:
            store_price_map[name]["nulls"] += 1
            
    high_null_price_stores = []
    for name, stats in store_price_map.items():
        if stats["total"] >= 5:
            null_rate = (stats["nulls"] / stats["total"]) * 100
            if null_rate > 20.0:
                high_null_price_stores.append({"name": name, "null_rate": round(null_rate, 1)})

    return jsonify({
        "null_price_count": null_price_count,
        "stale_price_count": stale_price_count,
        "avg_discount_percentage": avg_discount_percentage,
        "currency_mix": currency_mix,
        "discount_depth_ranking": discount_depth_ranking,
        "price_staleness_grid": price_staleness_grid,
        "all_oos_items_count": all_oos_items_count,
        "high_null_price_stores": high_null_price_stores
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
    network = request.args.get("network")
    country = request.args.get("country")
    sync_staleness = request.args.get("sync_staleness")
    
    pagination, serialized = _fetch_stores_page(page, per_page, search, network, country, sync_staleness)
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
        "source_header": {
            "name": source.name,
            "domain": source.domain,
            "logo_url": source.logo_url
        },
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
    
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    stale_date = now - timedelta(days=7)

    stats = db.session.execute(
        select(
            func.count(ItemStoreLink.id).label("total_links"),
            func.sum(case((ItemStoreLink.is_active == True, 1), else_=0)).label("active_links"),
            func.sum(case((ItemStoreLink.is_active == False, 1), else_=0)).label("inactive_links"),
            func.sum(case((ItemStoreLink.last_synced_at == None, 1), else_=0)).label("never_synced"),
            func.sum(case((ItemStoreLink.last_synced_at < stale_date, 1), else_=0)).label("stale_links"),
            func.sum(case((ItemStoreLink.availability == 'OutOfStock', 1), else_=0)).label("out_of_stock"),
            func.max(ItemStoreLink.last_synced_at).label("last_synced"),
            func.count(func.distinct(ItemStoreLink.program_name)).label("program_count"),
            func.avg(ItemStoreLink.commission_rate).label("avg_commission"),
            func.max(ItemStoreLink.commission_rate).label("max_commission"),
            func.sum(case((ItemStoreLink.commission_rate != None, 1), else_=0)).label("with_commission"),
            func.sum(case((ItemStoreLink.commission_rate == None, 1), else_=0)).label("without_commission"),
            func.sum(case((ItemStoreLink.tracking_code != None, 1), else_=0)).label("with_tracking"),
            func.min(ItemStoreLink.price).label("min_price"),
            func.avg(ItemStoreLink.price).label("avg_price"),
            func.max(ItemStoreLink.price).label("max_price"),
            func.sum(case(((ItemStoreLink.old_price != None) & (ItemStoreLink.old_price > ItemStoreLink.price), 1), else_=0)).label("with_discount"),
            func.avg(case(((ItemStoreLink.old_price != None) & (ItemStoreLink.old_price > ItemStoreLink.price), (ItemStoreLink.old_price - ItemStoreLink.price) / ItemStoreLink.old_price * 100), else_=None)).label("avg_discount_pct"),
            func.sum(case((ItemStoreLink.price == None, 1), else_=0)).label("null_price")
        )
        .where(ItemStoreLink.store_id == id)
    ).first()
    
    currency_mix_rows = db.session.execute(
        select(ItemStoreLink.currency, func.count(ItemStoreLink.id))
        .where(ItemStoreLink.store_id == id)
        .where(ItemStoreLink.currency != None)
        .group_by(ItemStoreLink.currency)
    ).all()
    currency_mix = ", ".join(f"{c[0]}: {c[1]}" for c in currency_mix_rows) if currency_mix_rows else "—"

    # Quick Python calculation for avg sync age
    all_syncs = db.session.execute(
        select(ItemStoreLink.last_synced_at)
        .where(ItemStoreLink.store_id == id)
        .where(ItemStoreLink.last_synced_at != None)
    ).all()
    total_days = 0
    for (dt,) in all_syncs:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        total_days += (now - dt).days
    avg_sync_age = round(total_days / len(all_syncs), 1) if all_syncs else "—"

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
        "active links": str(stats.active_links or 0),
        "avg commission": f"{round(float(stats.avg_commission), 2)}%" if stats.avg_commission is not None else "—",
        "country": store.country or "—",
        "currency": store.currency or "—",
        "api enabled": "Yes" if store.api_enabled else "No",
        "total links": str(stats.total_links or 0),
        "inactive links": str(stats.inactive_links or 0),
        "never synced": str(stats.never_synced or 0),
        "stale links (7d)": str(stats.stale_links or 0),
        "out of stock": str(stats.out_of_stock or 0),
        "avg sync age (days)": str(avg_sync_age),
        "last synced at": stats.last_synced.strftime('%Y-%m-%d %H:%M') if stats.last_synced else "—",
        "feed enabled": "Yes" if store.feed_enabled else "No",
        "network slug": store.network_slug or "—",
        "program count": str(stats.program_count or 0),
        "avg commission rate": f"{round(float(stats.avg_commission), 2)}%" if stats.avg_commission is not None else "—",
        "max commission rate": f"{round(float(stats.max_commission), 2)}%" if stats.max_commission is not None else "—",
        "links with commission": str(stats.with_commission or 0),
        "links without commission": str(stats.without_commission or 0),
        "links with tracking code": str(stats.with_tracking or 0),
        "min price": str(round(float(stats.min_price), 2)) if stats.min_price is not None else "—",
        "avg price": str(round(float(stats.avg_price), 2)) if stats.avg_price is not None else "—",
        "max price": str(round(float(stats.max_price), 2)) if stats.max_price is not None else "—",
        "links with discount": str(stats.with_discount or 0),
        "avg discount %": f"{round(float(stats.avg_discount_pct), 1)}%" if stats.avg_discount_pct is not None else "—",
        "links with null price": str(stats.null_price or 0),
        "currency mix": currency_mix
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
        return "Source not found.", 404
    return render_template("admin/components/_inspect.html", **data)


@bp.route("/stores/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_store(id):
    data = build_store_inspect_data(id)
    if not data:
        return "Store not found.", 404
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

