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
                func.sum(LastAPIFetch.failure_count).label("failure_count")
            )
            .where(func.lower(LastAPIFetch.source).in_([sl.lower() for sl in page_source_slugs]))
            .group_by(LastAPIFetch.source)
        ).all()
        fetch_agg_map = {r.source.lower(): r for r in fetch_agg}
    else:
        content_agg_map, fetch_agg_map = {}, {}

    serialized = []
    for s in pagination.items:
        agg             = content_agg_map.get(s.id)
        content_count   = agg.content_count if agg else 0
        latest_activity = agg.latest_ingested_at.isoformat() if agg and agg.latest_ingested_at else None
        engagement      = int(agg.engagement) if agg and agg.engagement is not None else 0
        fetch_info      = fetch_agg_map.get(s.slug.lower())
        last_crawl      = fetch_info.last_crawl.isoformat() if fetch_info and fetch_info.last_crawl else None
        success_count   = fetch_info.success_count if (fetch_info and fetch_info.success_count is not None) else 0
        failure_count   = fetch_info.failure_count if (fetch_info and fetch_info.failure_count is not None) else 0
        total_fetches   = success_count + failure_count
        success_rate    = round((success_count / total_fetches) * 100.0, 1) if total_fetches > 0 else 100.0
        if not s.is_active:
            status_val = "failed"
        elif content_count == 0 or success_rate < 80.0:
            status_val = "warning"
        else:
            status_val = "healthy"
        serialized.append({
            "id":              s.id,
            "link":              {'url': f'https://{s.domain}', 'name': s.name},
            "content-count":   content_count,
            "last-crawl":      last_crawl,
            "success-rate":    success_rate,
            "failure-count":   failure_count,
            "engagement":      engagement,
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

@bp.route("/sources/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_source(id):
    source = db.session.get(Source, id)
    if not source:
        return "<p class='text-muted'>Source not found.</p>", 404
        
    content_count = db.session.scalar(select(func.count(Content.id)).filter(Content.source_id == id)) or 0
    from app.admin.helpers import format_status
    from app.admin.tables import get_inspect_table
    
    data = {
        "id": f"#{source.id}",
        "name": source.name,
        "slug": source.slug,
        "domain": source.domain,
        "status": format_status(source.is_active),
        "authority score": str(source.authority_score),
        "content count": str(content_count),
    }
    inspect_table = get_inspect_table("sources", data)
    
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table)


@bp.route("/stores/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_store(id):
    store = db.session.get(Store, id)
    if not store:
        return "<p class='text-muted'>Store not found.</p>", 404
        
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
    }
    inspect_table = get_inspect_table("stores", data)
    
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table)
