# app/admin/stats.py
"""
Admin dashboard statistics and top-list endpoints.

Performance optimisations applied:
- Provider activity: N+1 loop (4 queries × N sources) replaced with 2
  aggregate queries joined in Python (R-02).
- Inactive content count derived arithmetically from total − active (R-16).
- 7-day growth trend uses a single GROUP BY query instead of a per-day loop (R-17).
- Interaction breakdown reads from the 60-second cached get_interactions_breakdown() (R-03).
- All queries use SQLAlchemy 2.0-style select() (R-07).
"""
from flask import Blueprint, jsonify, render_template
from app.core.extensions import db
from app.core.decorators import admin_required
from app.domains.content.models import Content
from app.domains.taxonomy.models import Category, Source
from app.domains.item.models import Item
from app.domains.user.models import User
from app.domains.interaction.service.query import get_interactions_breakdown, get_reaction_stats
from sqlalchemy import func, select, cast, Date
from datetime import datetime, timedelta, timezone

bp = Blueprint("api_dashboard", __name__, url_prefix="/admin/dashboard")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all dashboard endpoints require admin privilege."""
    pass


def get_dashboard_stats_data():
    """Consolidated helper to compute all dashboard statistics."""
    # ── Interaction stats (single cached call) ────────────────────────────
    breakdown = get_interactions_breakdown()
    total_interactions = sum(v for k, v in breakdown.items() if not k.startswith("_"))

    # ── Catalog grand totals ──────────────────────────────────────────────
    contents_count = db.session.execute(select(func.count(Content.id))).scalar() or 0
    items_count    = db.session.execute(select(func.count(Item.id))).scalar() or 0
    users_count    = db.session.execute(select(func.count(User.id))).scalar() or 0

    # ── Active / Inactive distribution ───────────────────────────────────
    active_contents   = db.session.execute(
        select(func.count(Content.id)).where(Content.is_active == True)
    ).scalar() or 0
    inactive_contents = contents_count - active_contents

    # ── Review queue ─────────────────────────────────────────────────────
    review_queue_count = db.session.execute(
        select(func.count(Content.id)).where(Content.is_published == False)
    ).scalar() or 0

    # ── Content breakdown by type ─────────────────────────────────────────
    by_type_rows = db.session.execute(
        select(Content.object_type, func.count(Content.id).label("cnt"))
        .group_by(Content.object_type)
    ).all()
    by_type_map = {r.object_type: r.cnt for r in by_type_rows}
    type_distribution = {
        "article": by_type_map.get("article", 0),
        "video":   by_type_map.get("video", 0),
        "post":    by_type_map.get("post", 0),
    }

    # ── Category distribution (top 6) ────────────────────────────────────
    by_category_rows = db.session.execute(
        select(Category.name, Category.slug, func.count(Content.id).label("cnt"))
        .join(Content.category)
        .group_by(Category.name, Category.slug)
        .order_by(func.count(Content.id).desc())
        .limit(6)
    ).all()
    category_distribution = [{"name": r.name, "slug": r.slug, "count": r.cnt} for r in by_category_rows]

    # ── Content by source (top 10) ────────────────────────────────────────
    content_by_source_rows = db.session.execute(
        select(Source.name, Source.slug, func.count(Content.id).label("cnt"))
        .join(Content.source)
        .group_by(Source.name, Source.slug)
        .order_by(func.count(Content.id).desc())
        .limit(10)
    ).all()
    content_by_source = [{"name": r.name, "slug": r.slug, "count": r.cnt} for r in content_by_source_rows]

    # ── Product by source ─────────────────────────────────────────────────
    product_by_source_rows = db.session.execute(
        select(Source.name, Source.slug, func.count(Item.id).label("cnt"))
        .join(Item.source)
        .group_by(Source.name, Source.slug)
        .order_by(func.count(Item.id).desc())
    ).all()
    product_by_source = [{"name": r.name, "slug": r.slug, "count": r.cnt} for r in product_by_source_rows]

    # ── Top performing content providers (by total views) ─────────────────
    top_content_rows = db.session.execute(
        select(Source.name, Source.slug, func.sum(Content.view_count).label("total_views"))
        .join(Content.source)
        .group_by(Source.name, Source.slug)
        .order_by(func.sum(Content.view_count).desc())
        .limit(6)
    ).all()
    top_performing_content = [{"name": r.name, "slug": r.slug, "views": int(r.total_views or 0)} for r in top_content_rows]

    # ── Top performing product providers (by total clicks) ───────────────
    top_product_rows = db.session.execute(
        select(Source.name, Source.slug, func.sum(Item.click_count).label("total_clicks"))
        .join(Item.source)
        .group_by(Source.name, Source.slug)
        .order_by(func.sum(Item.click_count).desc())
        .limit(6)
    ).all()
    top_performing_product = [{"name": r.name, "slug": r.slug, "clicks": int(r.total_clicks or 0)} for r in top_product_rows]

    # ── Provider activity summary ─────────────────────────────────────────
    content_agg = db.session.execute(
        select(
            Content.source_id,
            func.count(Content.id).label("c_count"),
            func.max(Content.ingested_at).label("latest_content"),
        )
        .where(Content.source_id != None)
        .group_by(Content.source_id)
    ).all()

    item_agg = db.session.execute(
        select(
            Item.source_id,
            func.count(Item.id).label("i_count"),
            func.max(Item.created_at).label("latest_item"),
        )
        .where(Item.source_id != None)
        .group_by(Item.source_id)
    ).all()

    all_source_ids = {r.source_id for r in content_agg} | {r.source_id for r in item_agg}
    source_map = {}
    if all_source_ids:
        source_rows = db.session.execute(
            select(Source.id, Source.name, Source.slug)
            .where(Source.id.in_(all_source_ids))
        ).all()
        source_map = {r.id: {"name": r.name, "slug": r.slug} for r in source_rows}

    content_by_sid = {r.source_id: r for r in content_agg}
    item_by_sid    = {r.source_id: r for r in item_agg}
    provider_activities = []
    for sid in all_source_ids:
        src_info = source_map.get(sid)
        if not src_info:
            continue
        c_row = content_by_sid.get(sid)
        i_row = item_by_sid.get(sid)
        c_count = c_row.c_count if c_row else 0
        i_count = i_row.i_count if i_row else 0
        if c_count == 0 and i_count == 0:
            continue

        latest_c = c_row.latest_content if c_row else None
        latest_i = i_row.latest_item if i_row else None
        if latest_c and latest_i:
            latest_activity = max(latest_c, latest_i)
        else:
            latest_activity = latest_c or latest_i

        provider_activities.append({
            "name":            src_info["name"],
            "slug":            src_info["slug"],
            "content_count":   c_count,
            "product_count":   i_count,
            "latest_activity": latest_activity.isoformat() if latest_activity else None,
        })

    provider_activities.sort(
        key=lambda x: x["content_count"] + x["product_count"],
        reverse=True
    )
    provider_activities = provider_activities[:10]

    # ── 7-day growth trend ────────────────────────────────────────────────
    today = datetime.now(timezone.utc).date()
    week_start = datetime.combine(today - timedelta(days=6), datetime.min.time())

    trend_rows = db.session.execute(
        select(
            cast(Content.published_at, Date).label("day"),
            func.count(Content.id).label("cnt"),
        )
        .where(Content.published_at >= week_start)
        .group_by(cast(Content.published_at, Date))
    ).all()

    trend_map = {r.day: r.cnt for r in trend_rows}
    growth_trends = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        growth_trends.append({
            "date":  day.strftime("%b %d"),
            "count": trend_map.get(day, 0),
        })

    # ── Recently ingested (latest 5) ──────────────────────────────────────
    recent_rows = db.session.execute(
        select(Content.id, Content.title, Content.object_type, Content.ingested_at)
        .order_by(Content.ingested_at.desc())
        .limit(5)
    ).mappings().all()

    now = datetime.now(timezone.utc)
    recent_ingested = []
    for r in recent_rows:
        ingested_at = r["ingested_at"]
        if ingested_at.tzinfo is None:
            ingested_at = ingested_at.replace(tzinfo=timezone.utc)
        diff = now - ingested_at
        if diff.days > 0:
            time_str = f"{diff.days}d ago"
        elif diff.seconds >= 3600:
            time_str = f"{diff.seconds // 3600}h ago"
        elif diff.seconds >= 60:
            time_str = f"{diff.seconds // 60}m ago"
        else:
            time_str = "Just now"

        recent_ingested.append({
            "id":    r["id"],
            "title": r["title"] or f"Untitled ({r['object_type']})",
            "type":  r["object_type"],
            "time":  time_str,
        })

    return {
        "contents_count":         contents_count,
        "items_count":            items_count,
        "users_count":            users_count,
        "active_contents":        active_contents,
        "inactive_contents":      inactive_contents,
        "review_queue_count":     review_queue_count,
        "by_type":                type_distribution,
        "by_category":            category_distribution,
        "by_source":              content_by_source,
        "product_by_source":      product_by_source,
        "top_performing_content": top_performing_content,
        "top_performing_product": top_performing_product,
        "provider_activities":    provider_activities,
        "growth_trends":          growth_trends,
        "recent_ingested":        recent_ingested,
        "interactions": {
            "total":     total_interactions,
            "views":     breakdown.get("views", 0),
            "comments":  breakdown.get("comments", 0),
            "reactions": breakdown.get("reactions", 0),
            "saves":     breakdown.get("saves", 0),
            "shares":    breakdown.get("shares", 0),
            "clicks":    breakdown.get("clicks", 0),
            "likes":     breakdown.get("_likes", 0),
            "dislikes":  breakdown.get("_dislikes", 0),
        },
    }


# ─────────────────────────────────────────────
# MAIN STATS ENDPOINT
# ─────────────────────────────────────────────

@bp.route("/stats", methods=["GET"])
def dashboard_stats():
    """Enhanced dashboard metrics, aggregates, distributions, and trends."""
    return jsonify(get_dashboard_stats_data())


# ─────────────────────────────────────────────
# WIDGET ENDPOINTS
# ─────────────────────────────────────────────

@bp.route("/widget/stats", methods=["GET"])
def widget_stats():
    data = get_dashboard_stats_data()
    return render_template("admin/dashboard/widgets/_stats_grid.html", stats=data)


@bp.route("/widget/catalog-health", methods=["GET"])
def widget_catalog_health():
    data = get_dashboard_stats_data()
    return render_template("admin/dashboard/widgets/_catalog_health.html", data=data)


@bp.route("/widget/recent-ingest", methods=["GET"])
def widget_recent_ingest():
    data = get_dashboard_stats_data()
    return render_template("admin/dashboard/widgets/_recent_ingest.html", recent_ingested=data.get("recent_ingested", []))


@bp.route("/widget/categories-distribution", methods=["GET"])
def widget_categories_distribution():
    data = get_dashboard_stats_data()
    return render_template("admin/dashboard/widgets/_categories_distribution.html", by_category=data.get("by_category", []))


@bp.route("/widget/sources-distribution", methods=["GET"])
def widget_sources_distribution():
    data = get_dashboard_stats_data()
    return render_template("admin/dashboard/widgets/_sources_distribution.html", by_source=data.get("by_source", []))


@bp.route("/widget/product-sources-distribution", methods=["GET"])
def widget_product_sources_distribution():
    data = get_dashboard_stats_data()
    return render_template("admin/dashboard/widgets/_product_sources_distribution.html", product_by_source=data.get("product_by_source", []))


@bp.route("/widget/top-content-providers", methods=["GET"])
def widget_top_content_providers():
    data = get_dashboard_stats_data()
    return render_template("admin/dashboard/widgets/_top_content_providers.html", top_performing_content=data.get("top_performing_content", []))


@bp.route("/widget/top-product-providers", methods=["GET"])
def widget_top_product_providers():
    data = get_dashboard_stats_data()
    return render_template("admin/dashboard/widgets/_top_product_providers.html", top_performing_product=data.get("top_performing_product", []))


@bp.route("/widget/provider-activities", methods=["GET"])
def widget_provider_activities():
    data = get_dashboard_stats_data()
    activities = data.get("provider_activities", [])
    for act in activities:
        if act.get("latest_activity"):
            try:
                dt = datetime.fromisoformat(act["latest_activity"])
                act["latest_activity_formatted"] = dt.strftime("%b %d, %Y")
            except Exception:
                act["latest_activity_formatted"] = act["latest_activity"]
        else:
            act["latest_activity_formatted"] = "No activity"
    return render_template("admin/dashboard/widgets/_provider_activities.html", provider_activities=activities)


@bp.route("/widget/top-articles", methods=["GET"])
def widget_top_articles():
    rows = db.session.execute(
        select(Content.id, Content.title, Content.object_type, Content.view_count)
        .order_by(Content.view_count.desc())
        .limit(5)
    ).mappings().all()
    items = [{
        "id":         r["id"],
        "title":      r["title"] or f"{r['object_type'].capitalize()} #{r['id']}",
        "type":       r["object_type"],
        "view_count": r["view_count"] or 0,
    } for r in rows]
    return render_template("admin/dashboard/widgets/_top_articles.html", items=items)


@bp.route("/widget/top-items", methods=["GET"])
def widget_top_items():
    rows = db.session.execute(
        select(Item.id, Item.name, Item.item_type, Item.click_count, Item.rating)
        .order_by(Item.click_count.desc())
        .limit(5)
    ).mappings().all()
    items = [{
        "id":          r["id"],
        "name":        r["name"],
        "item_type":   r["item_type"],
        "click_count": r["click_count"] or 0,
        "rating":      r["rating"],
    } for r in rows]
    return render_template("admin/dashboard/widgets/_top_items.html", items=items)


@bp.route("/widget/interactions-breakdown", methods=["GET"])
def widget_interactions_breakdown():
    data = get_dashboard_stats_data()
    return render_template("admin/dashboard/widgets/_interactions_breakdown.html", interactions=data.get("interactions", {}))


# ─────────────────────────────────────────────
# TOP CONTENT & ITEMS JSON ENDPOINTS (keep for backwards compat if needed)
# ─────────────────────────────────────────────

@bp.route("/top-contents", methods=["GET"])
def top_contents():
    """Top 5 content items by view count for the overview panel."""
    rows = db.session.execute(
        select(Content.id, Content.title, Content.object_type, Content.view_count)
        .order_by(Content.view_count.desc())
        .limit(5)
    ).mappings().all()
    return jsonify([{
        "id":         r["id"],
        "title":      r["title"] or f"{r['object_type'].capitalize()} #{r['id']}",
        "type":       r["object_type"],
        "view_count": r["view_count"] or 0,
    } for r in rows])


@bp.route("/top-items", methods=["GET"])
def top_items():
    """Top 5 items by click count for the overview panel."""
    rows = db.session.execute(
        select(Item.id, Item.name, Item.item_type, Item.click_count, Item.rating)
        .order_by(Item.click_count.desc())
        .limit(5)
    ).mappings().all()
    return jsonify([{
        "id":          r["id"],
        "name":        r["name"],
        "item_type":   r["item_type"],
        "click_count": r["click_count"] or 0,
        "rating":      r["rating"],
    } for r in rows])
