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

    # ── Aggregate: content count + latest ingested_at per source ──────────
    content_agg = db.session.execute(
        select(
            Content.source_id,
            func.count(Content.id).label("content_count"),
            func.max(Content.ingested_at).label("latest_ingested_at"),
        )
        .where(Content.source_id.in_(page_source_ids))
        .group_by(Content.source_id)
    ).all()
    content_agg_map = {r.source_id: r for r in content_agg}

    serialized = []
    for s in pagination.items:
        agg = content_agg_map.get(s.id)

        content_count   = agg.content_count if agg else 0
        latest_activity = agg.latest_ingested_at.isoformat() if agg and agg.latest_ingested_at else None

        if not s.is_active:
            status_val = "failed"
        elif content_count == 0:
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
