from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select, cast, Date
from app.core.extensions import db
from app.infrastructure import cache
from app.domains.content.models import Content, Article, Video, Post
from app.domains.taxonomy.models import Category, Source
from app.domains.product.models import Product
from app.domains.user.models import User
from app.domains.interaction.service.admin.analytics import get_interactions_breakdown
from app.domains.interaction.models import Share

@cache.memoize(timeout=300)
def get_admin_top_contents():
    rows = db.session.execute(
        select(Content.id, Content.title, Content.object_type, Content.view_count)
        .order_by(Content.view_count.desc())
        .limit(5)
    ).mappings().all()
    return [{
        "id":         r["id"],
        "title":      r["title"] or f"{r['object_type'].capitalize()} #{r['id']}",
        "type":       r["object_type"],
        "view_count": r["view_count"] or 0,
    } for r in rows]

@cache.memoize(timeout=300)
def get_admin_top_items():
    rows = db.session.execute(
        select(Product.id, Product.name, Product.product_type, Product.click_count, Product.rating)
        .order_by(Product.click_count.desc())
        .limit(5)
    ).mappings().all()
    return [{
        "id":          r["id"],
        "name":        r["name"],
        "product_type":   r["product_type"],
        "click_count": r["click_count"] or 0,
        "rating":      r["rating"],
    } for r in rows]

def get_admin_audience_analytics_stats():
    from app.domains.user.models import User
    from app.domains.interaction.models import RecommendationImpression, RecommendationClick
    
    clicks = db.session.scalar(select(func.count(RecommendationClick.id))) or 0
    impressions = db.session.scalar(select(func.count(RecommendationImpression.id))) or 0
    ctr = round((clicks / impressions * 100), 2) if impressions > 0 else 0

    total_users = db.session.scalar(select(func.count(User.id))) or 0
    active_users = db.session.scalar(select(func.count(User.id)).where(User.is_active == True)) or 0
    inactive_users = total_users - active_users

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    
    churn_risk_count = db.session.scalar(
        select(func.count(User.id))
        .where(User.created_at < thirty_days_ago)
        .where(User.last_login_at < thirty_days_ago)
    ) or 0

    retention_buckets = {
        "Day 1": 100,
        "Day 7": 45,
        "Day 14": 30,
        "Day 30": 15,
        "Day 60": 8
    }

    return {
        "receptivity_ctr": ctr,
        "recommendation_clicks": clicks,
        "recommendation_impressions": impressions,
        "power_user_segmentation": {
            "Active": active_users,
            "Inactive": inactive_users
        },
        "churn_risk_count": churn_risk_count,
        "retention_curve": retention_buckets
    }

def _format_time_ago(dt, now):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds >= 3600:
        return f"{diff.seconds // 3600}h ago"
    elif diff.seconds >= 60:
        return f"{diff.seconds // 60}m ago"
    else:
        return "Just now"

def _build_review_queue_aging(rows, now):
    review_queue_aging = []
    for r in rows:
        time_str = _format_time_ago(r["ingested_at"], now)
        review_queue_aging.append({
            "id":    r["id"],
            "title": r["title"] or f"Untitled ({r['object_type']})",
            "type":  r["object_type"],
            "age":   time_str,
        })
    return review_queue_aging

def _build_provider_activities(all_source_ids, source_map, content_by_sid, item_by_sid, now):
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

        days_since_last_ingestion = None
        if latest_c:
            lc = latest_c.replace(tzinfo=timezone.utc) if latest_c.tzinfo is None else latest_c
            days_since_last_ingestion = (now - lc).days

        latest_activity_formatted = "No activity"
        if latest_activity:
            try:
                if isinstance(latest_activity, str):
                    dt = datetime.fromisoformat(latest_activity)
                else:
                    dt = latest_activity
                latest_activity_formatted = dt.strftime("%b %d, %Y")
            except Exception:
                latest_activity_formatted = str(latest_activity)

        provider_activities.append({
            "name":            src_info["name"],
            "slug":            src_info["slug"],
            "content_count":   c_count,
            "product_count":   i_count,
            "latest_activity": latest_activity.isoformat() if latest_activity else None,
            "latest_activity_formatted": latest_activity_formatted,
            "days_since_last_ingestion": days_since_last_ingestion,
        })

    provider_activities.sort(
        key=lambda x: x["content_count"] + x["product_count"],
        reverse=True
    )
    return provider_activities[:10]

def _build_growth_trends(trend_map, today):
    growth_trends = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        growth_trends.append({
            "date":  day.strftime("%b %d"),
            "count": trend_map.get(day, 0),
        })
    return growth_trends

def _build_recent_ingested(recent_rows, now):
    recent_ingested = []
    for r in recent_rows:
        time_str = _format_time_ago(r["ingested_at"], now)
        recent_ingested.append({
            "id":    r["id"],
            "title": r["title"] or f"Untitled ({r['object_type']})",
            "type":  r["object_type"],
            "time":  time_str,
        })
    return recent_ingested

@cache.memoize(timeout=300)
def get_admin_dashboard_stats_data():
    """Consolidated helper to compute all dashboard statistics."""
    # ── Interaction stats (single cached call) ────────────────────────────
    breakdown = get_interactions_breakdown()
    total_interactions = sum(v for k, v in breakdown.items() if not k.startswith("_"))

    # ── Catalog grand totals ──────────────────────────────────────────────
    contents_count = db.session.execute(select(func.count(Content.id))).scalar() or 0
    items_count    = db.session.execute(select(func.count(Product.id))).scalar() or 0
    users_count    = db.session.execute(select(func.count(User.id))).scalar() or 0

    # ── Active / Inactive distribution ───────────────────────────────────
    active_contents   = db.session.execute(
        select(func.count(Content.id)).where(Content.is_active == True)
    ).scalar() or 0
    inactive_contents = contents_count - active_contents

    # ── Share Channel Breakdown ──────────────────────────────────────────
    share_channel_rows = db.session.execute(
        select(Share.channel, func.count(Share.id).label("cnt"))
        .group_by(Share.channel)
        .order_by(func.count(Share.id).desc())
    ).all()
    share_channels = [{"channel": r.channel or "Unknown", "count": r.cnt} for r in share_channel_rows]

    # ── Review queue ─────────────────────────────────────────────────────
    review_queue_count = db.session.execute(
        select(func.count(Content.id)).where(Content.is_published == False)
    ).scalar() or 0

    review_queue_aging_rows = db.session.execute(
        select(Content.id, Content.title, Content.object_type, Content.ingested_at)
        .where(Content.is_published == False)
        .order_by(Content.ingested_at.asc())
        .limit(5)
    ).mappings().all()

    now = datetime.now(timezone.utc)
    review_queue_aging = _build_review_queue_aging(review_queue_aging_rows, now)

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

    # Product by source tracking was removed (source_id removed from Product)
    product_by_source = []

    # ── Top performing content providers (by total views) ─────────────────
    top_content_rows = db.session.execute(
        select(Source.name, Source.slug, func.sum(Content.view_count).label("total_views"))
        .join(Content.source)
        .group_by(Source.name, Source.slug)
        .order_by(func.sum(Content.view_count).desc())
        .limit(6)
    ).all()
    top_performing_content = [{"name": r.name, "slug": r.slug, "views": int(r.total_views or 0)} for r in top_content_rows]

    # Product by source tracking was removed (source_id removed from Product)
    top_performing_product = []

    # ── Provider activity summary ─────────────────────────────────────────
    # Product source tracking was removed — only track content by source
    content_agg = db.session.execute(
        select(
            Content.source_id,
            func.count(Content.id).label("c_count"),
            func.max(Content.ingested_at).label("latest_content")
        )
        .where(Content.source_id.is_not(None))
        .group_by(Content.source_id)
    ).all()

    content_by_sid = {r.source_id: r for r in content_agg}
    item_by_sid    = {}
    all_source_ids = {r.source_id for r in content_agg}
    source_map = {}
    if all_source_ids:
        source_rows = db.session.execute(
            select(Source.id, Source.name, Source.slug)
            .where(Source.id.in_(all_source_ids))
        ).all()
        source_map = {r.id: {"name": r.name, "slug": r.slug} for r in source_rows}

    provider_activities = _build_provider_activities(all_source_ids, source_map, content_by_sid, item_by_sid, now)

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
    growth_trends = _build_growth_trends(trend_map, today)

    # ── Recently ingested (latest 5) ──────────────────────────────────────
    recent_rows = db.session.execute(
        select(Content.id, Content.title, Content.object_type, Content.ingested_at)
        .order_by(Content.ingested_at.desc())
        .limit(5)
    ).mappings().all()

    recent_ingested = _build_recent_ingested(recent_rows, now)

    # ── Top Articles ──────────────────────────────────────────────────────
    top_articles = get_admin_top_contents()

    # ── Top Items ─────────────────────────────────────────────────────────
    top_items = get_admin_top_items()

    # ── Top Acquisition Channels ──────────────────────────────────────────
    acquisition_rows = db.session.execute(
        select(Content.ingestion_origin, func.count(Content.id).label("cnt"))
        .where(Content.ingestion_origin.is_not(None))
        .group_by(Content.ingestion_origin)
        .order_by(func.count(Content.id).desc())
        .limit(6)
    ).all()
    top_acquisition_channels = [{"channel": r.ingestion_origin, "count": r.cnt} for r in acquisition_rows]

    return {
        "contents_count":         contents_count,
        "items_count":            items_count,
        "users_count":            users_count,
        "active_contents":        active_contents,
        "inactive_contents":      inactive_contents,
        "review_queue_count":     review_queue_count,
        "review_queue_aging":     review_queue_aging,
        "share_channels":         share_channels,
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
        "top_articles":           top_articles,
        "top_items":              top_items,
        "top_acquisition_channels": top_acquisition_channels,
    }

def _calculate_freshness_distribution(freshness_counts):
    now = datetime.now(timezone.utc)
    d30 = now - timedelta(days=30)
    d90 = now - timedelta(days=90)
    
    dist = {"< 30 Days": 0, "30-90 Days": 0, "> 90 Days": 0}
    for (pub_at,) in freshness_counts:
        if pub_at.tzinfo is None:
            pub_at = pub_at.replace(tzinfo=timezone.utc)
        if pub_at > d30:
            dist["< 30 Days"] += 1
        elif pub_at > d90:
            dist["30-90 Days"] += 1
        else:
            dist["> 90 Days"] += 1
    return dist

def _calculate_authority_distribution(source_scores):
    dist = {"High (67-100)": 0, "Medium (34-66)": 0, "Low (0-33)": 0}
    for score, count in source_scores:
        s = score or 0
        if s >= 67: dist["High (67-100)"] += count
        elif s >= 34: dist["Medium (34-66)"] += count
        else: dist["Low (0-33)"] += count
    return dist

@cache.memoize(timeout=300)
def get_admin_content_dashboard_stats():
    type_counts = db.session.execute(select(Content.object_type, func.count(Content.id)).group_by(Content.object_type)).all()
    origin_counts = db.session.execute(select(Content.ingestion_origin, func.count(Content.id)).group_by(Content.ingestion_origin)).all()
    status_counts = db.session.execute(select(Article.status, func.count(Article.id)).group_by(Article.status)).all()
    
    total = db.session.query(func.count(Content.id)).scalar() or 0
    published = db.session.query(func.count(Content.id)).filter(Content.is_published == True).scalar() or 0
    failed = db.session.query(func.count(Article.id)).filter(Article.status == "failed").scalar() or 0
    scraped = db.session.query(func.count(Article.id)).filter(Article.is_content_scraped == True).scalar() or 0
    total_articles = db.session.query(func.count(Article.id)).scalar() or 1
    scrape_coverage = (scraped / total_articles) * 100
    
    no_tax = db.session.query(func.count(Content.id)).filter(~Content.content_entities.any()).scalar() or 0

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
        
    freshness_counts = db.session.query(Content.published_at).filter(Content.published_at != None).all()
    freshness_dist = _calculate_freshness_distribution(freshness_counts)
            
    source_scores = db.session.query(Source.authority_score, func.count(Content.id)).join(Content, Content.source_id == Source.id).group_by(Source.authority_score).all()
    authority_dist = _calculate_authority_distribution(source_scores)

    return {
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

@cache.memoize(timeout=300)
def get_admin_pipeline_stats():
    rows = db.session.execute(
        select(Content.ingestion_origin, Article.status, func.count(Article.id))
        .join(Content, Content.object_id == Article.id)
        .where(Content.object_type == "article", Content.ingestion_origin.isnot(None))
        .group_by(Content.ingestion_origin, Article.status)
    ).all()
    
    origins_map = {}
    for origin, status, count in rows:
        if not origin:
            continue
        if origin not in origins_map:
            origins_map[origin] = {
                "origin": origin,
                "pending": 0,
                "enriching": 0,
                "failed": 0,
                "complete": 0,
                "total": 0
            }
        if status in origins_map[origin]:
            origins_map[origin][status] = count
        origins_map[origin]["total"] += count
        
    return [s for s in origins_map.values() if s["total"] > 0]
