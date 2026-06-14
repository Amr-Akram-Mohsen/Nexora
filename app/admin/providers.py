# app/admin/providers.py
"""
Admin provider management endpoints (sources and stores).

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- N+1 loops replaced with aggregate subqueries for content/item counts and
  latest activity per provider (R-04).
- All queries use modern select() style (R-07).
- Shared pagination helpers from app.admin.helpers (R-18, R-21).
"""
from flask import Blueprint, jsonify, request
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.taxonomy.models import Source
from app.domains.content.models import Content
from app.domains.item.models import Store, Item, ItemVariant, ItemStoreLink
from app.domains.external.models import LastAPIFetch
from app.domains.interaction.models import View, ItemClick
from app.admin.helpers import parse_pagination_params
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

@bp.route("/sources", methods=["GET"])
def list_sources():
    """Paginated listing of sources/content providers with counts and latest content."""
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()

    stmt = select(Source)
    if search:
        term = f"%{search}%"
        stmt = stmt.where(or_(
            Source.name.ilike(term),
            Source.slug.ilike(term),
            Source.domain.ilike(term),
        ))
    stmt = stmt.order_by(Source.authority_score.desc(), Source.name.asc())

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    page_source_ids = [s.id for s in pagination.items]

    if not page_source_ids:
        return jsonify({
            "sources": [], "page": pagination.page,
            "pages": pagination.pages, "total": pagination.total,
            "per_page": pagination.per_page,
        })

    # ── Aggregate: content count + latest ingested_at + engagement per source ──────────
    content_agg = db.session.execute(
        select(
            Content.source_id,
            func.count(Content.id).label("content_count"),
            func.max(Content.ingested_at).label("latest_ingested_at"),
            func.sum(
                Content.view_count + Content.like_count + Content.dislike_count + Content.save_count + Content.comment_count
            ).label("engagement")
        )
        .where(Content.source_id.in_(page_source_ids))
        .group_by(Content.source_id)
    ).all()
    content_agg_map = {r.source_id: r for r in content_agg}

    # ── Fetch API health metrics from LastAPIFetch ─────────────────────
    page_source_slugs = [s.slug for s in pagination.items]
    fetch_agg = db.session.execute(
        select(
            LastAPIFetch.source,
            func.max(LastAPIFetch.last_fetched_at).label("last_crawl"),
            func.sum(LastAPIFetch.success_count).label("success_count"),
            func.sum(LastAPIFetch.failure_count).label("failure_count")
        )
        .where(func.lower(LastAPIFetch.source).in_([slug.lower() for slug in page_source_slugs]))
        .group_by(LastAPIFetch.source)
    ).all()
    fetch_agg_map = {r.source.lower(): r for r in fetch_agg}

    serialized = []
    for s in pagination.items:
        agg = content_agg_map.get(s.id)

        content_count   = agg.content_count if agg else 0
        latest_activity = agg.latest_ingested_at.isoformat() if agg and agg.latest_ingested_at else None
        engagement      = int(agg.engagement) if agg and agg.engagement is not None else 0

        # Crawl analytics
        fetch_info = fetch_agg_map.get(s.slug.lower())
        last_crawl = fetch_info.last_crawl.isoformat() if fetch_info and fetch_info.last_crawl else None
        success_count = fetch_info.success_count if (fetch_info and fetch_info.success_count is not None) else 0
        failure_count = fetch_info.failure_count if (fetch_info and fetch_info.failure_count is not None) else 0
        total_fetches = success_count + failure_count
        success_rate = round((success_count / total_fetches) * 100.0, 1) if total_fetches > 0 else 100.0

        if not s.is_active:
            status_val = "failed"
        elif content_count == 0 or success_rate < 80.0:
            status_val = "warning"
        else:
            status_val = "healthy"

        serialized.append({
            "id":              s.id,
            "name":            s.name,
            "slug":            s.slug,
            "domain":          s.domain,
            "logo_url":        s.logo_url,
            "is_active":       s.is_active,
            "authority_score": s.authority_score,
            "content_count":   content_count,
            "latest_activity": latest_activity,
            "last_crawl":      last_crawl,
            "success_rate":    success_rate,
            "failure_count":   failure_count,
            "engagement":      engagement,
            "status":          status_val,
        })

    return jsonify({
        "sources":  serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })


# ─────────────────────────────────────────────
# STORES (product / affiliate providers)
# ─────────────────────────────────────────────

@bp.route("/stores", methods=["GET"])
def list_stores():
    """Paginated listing of stores/commercial providers with counts and latest products."""
    page, per_page = parse_pagination_params(default_per_page=20)
    search = request.args.get("search", "").strip()

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

    if not page_store_ids:
        return jsonify({
            "stores": [], "page": pagination.page,
            "pages": pagination.pages, "total": pagination.total,
            "per_page": pagination.per_page,
        })

    # ── Aggregate: distinct item count per store (R-04) ───────────────────
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

    # ── Aggregate: total clicks per store ─────────────────────────────────
    clicks_rows = db.session.execute(
        select(
            ItemStoreLink.store_id,
            func.count(ItemClick.id).label("clicks")
        )
        .join(ItemClick, ItemClick.item_store_link_id == ItemStoreLink.id)
        .where(ItemStoreLink.store_id.in_(page_store_ids))
        .group_by(ItemStoreLink.store_id)
    ).all()
    clicks_map = {r.store_id: r.clicks for r in clicks_rows}

    # ── Aggregate: total views per store ──────────────────────────────────
    views_rows = db.session.execute(
        select(
            ItemStoreLink.store_id,
            func.count(View.id).label("views")
        )
        .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
        .join(View, (View.target_id == ItemVariant.item_id) & (View.target_type == 'item'))
        .where(ItemStoreLink.store_id.in_(page_store_ids))
        .group_by(ItemStoreLink.store_id)
    ).all()
    views_map = {r.store_id: r.views for r in views_rows}

    # ── Latest activity per store ─────────────────────────────────────────
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

    serialized = []
    for st in pagination.items:
        product_count = product_count_map.get(st.id, 0)
        latest_activity = latest_activity_map.get(st.id)
        latest_activity_str = latest_activity.isoformat() if latest_activity else None

        clicks = clicks_map.get(st.id, 0)
        views = views_map.get(st.id, 0)
        ctr = round((clicks / views) * 100.0, 2) if views > 0 else 0.0
        conversions = 0

        if not st.is_active:
            status_val = "failed"
        elif product_count == 0:
            status_val = "warning"
        else:
            status_val = "healthy"

        serialized.append({
            "id":                st.id,
            "name":              st.name,
            "slug":              st.slug,
            "website":           st.website,
            "affiliate_network": st.affiliate_network,
            "logo_url":          st.logo_url,
            "is_active":         st.is_active,
            "product_count":     product_count,
            "clicks":            clicks,
            "ctr":               ctr,
            "conversions":       conversions,
            "latest_activity":   latest_activity_str,
            "status":            status_val,
        })

    return jsonify({
        "stores":   serialized,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "total":    pagination.total,
        "per_page": pagination.per_page,
    })
