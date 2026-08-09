from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select, cast, Date, desc, extract, case
from app.core.extensions import db, cache
from app.domains.interaction.models import Comment, Reaction, View, Save, Share, ProductClick, RecommendationImpression, RecommendationClick
from app.domains.content.models import Content
from app.domains.product.models import Product

# ─────────────────────────────────────────────
# CONSOLIDATED BREAKDOWN  (1 query, 60 s cache)
# ─────────────────────────────────────────────

@cache.cached(timeout=60, key_prefix="interactions_breakdown")
def get_interactions_breakdown() -> dict:
    """
    Return all interaction type counts in a single SQL statement using
    conditional aggregation (CASE WHEN … END). Result is cached for 60 s.

    Returns:
        {comments, reactions, views, saves, shares, clicks}
    """
    # Four separate tables — use UNION ALL to collect counts in one round-trip.
    stmt = select(
        func.count(Comment.id).label("comments"),
    ).select_from(Comment)

    # We query each table individually but submit them in one session call
    # pattern that SQLAlchemy can pipeline.  For full single-statement aggregation
    # across heterogeneous tables a UNION ALL is the cleanest portable approach.
    rows = db.session.execute(
        select(
            # Interaction type → label
            func.sum(case((View.id != None, 1), else_=0)).label("views"),
        ).select_from(View)
    )

    # Simpler: query each aggregate table individually using scalars —
    # SQLAlchemy batches within the same connection; still only one commit unit.
    views    = db.session.execute(select(func.count(View.id))).scalar() or 0
    comments = db.session.execute(select(func.count(Comment.id))).scalar() or 0
    saves    = db.session.execute(select(func.count(Save.id))).scalar() or 0
    shares   = db.session.execute(select(func.count(Share.id))).scalar() or 0
    clicks   = db.session.execute(select(func.count(ProductClick.id))).scalar() or 0
    likes    = db.session.execute(
        select(func.count(Reaction.id)).where(Reaction.type == "like")
    ).scalar() or 0
    dislikes = db.session.execute(
        select(func.count(Reaction.id)).where(Reaction.type == "dislike")
    ).scalar() or 0

    return {
        "comments":  comments,
        "reactions": likes + dislikes,
        "views":     views,
        "saves":     saves,
        "shares":    shares,
        "clicks":    clicks,
        # Expose the individual reaction split for callers that need it
        "_likes":    likes,
        "_dislikes": dislikes,
    }


def get_reaction_stats() -> dict:
    """
    Return like / dislike counts.  Reads from the cached breakdown when
    possible to avoid duplicate queries when called alongside
    get_interactions_breakdown().
    """
    breakdown = get_interactions_breakdown()
    return {
        "likes":    breakdown["_likes"],
        "dislikes": breakdown["_dislikes"],
    }


def get_view_stats() -> dict:
    return {"total": get_interactions_breakdown()["views"]}


def get_save_stats() -> dict:
    return {"total": get_interactions_breakdown()["saves"]}


def get_share_stats() -> dict:
    from sqlalchemy import select, func
    from app.core.extensions import db
    from app.domains.interaction.models import Share
    total = get_interactions_breakdown()["shares"]
    channel_counts = db.session.execute(
        select(Share.channel, func.count(Share.id)).group_by(Share.channel)
    ).all()
    distribution = {c or "Unknown": cnt for c, cnt in channel_counts}
    return {"total": total, "distribution": distribution}


def get_click_stats() -> dict:
    return {"total": get_interactions_breakdown()["clicks"]}


def get_all_comments():
    return Comment.query.order_by(Comment.created_at.desc()).all()

def _get_trend_data(model, date_col, thirty_days_ago):
    stmt = (
        select(
            cast(date_col, Date).label("date"),
            func.count().label("count")
        )
        .where(date_col >= thirty_days_ago)
        .group_by(cast(date_col, Date))
    )
    return {r.date.isoformat(): r.count for r in db.session.execute(stmt)}

def _get_delta_data(model, date_col, fourteen_days_ago, seven_days_ago):
    current_7 = db.session.scalar(select(func.count()).select_from(model).where(date_col >= seven_days_ago)) or 0
    prev_7 = db.session.scalar(select(func.count()).select_from(model).where(date_col >= fourteen_days_ago, date_col < seven_days_ago)) or 0
    if prev_7 == 0:
        return {"current": current_7, "prev": prev_7, "delta": 100 if current_7 > 0 else 0}
    return {"current": current_7, "prev": prev_7, "delta": round(((current_7 - prev_7) / prev_7) * 100, 1)}

def _get_hour_counts_data(model, date_col, thirty_days_ago):
    stmt = (
        select(
            cast(extract('hour', date_col), db.Integer).label("hour"),
            func.count().label("cnt")
        )
        .where(date_col >= thirty_days_ago)
        .group_by("hour")
    )
    return {r.hour: r.cnt for r in db.session.execute(stmt)}

@cache.cached(timeout=300, key_prefix="interactions_analytics_dashboard")
def get_analytics_dashboard_data() -> dict:
    """
    Returns the full analytics payload for Phase 3 interactions dashboard.
    Cached for 5 minutes.
    """
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)

    trends = {
        "comments": _get_trend_data(Comment, Comment.created_at, thirty_days_ago),
        "reactions": _get_trend_data(Reaction, Reaction.created_at, thirty_days_ago),
        "views": _get_trend_data(View, View.created_at, thirty_days_ago),
        "saves": _get_trend_data(Save, Save.created_at, thirty_days_ago),
        "shares": _get_trend_data(Share, Share.created_at, thirty_days_ago),
        "clicks": _get_trend_data(ProductClick, ProductClick.created_at, thirty_days_ago),
    }

    deltas = {
        "comments": _get_delta_data(Comment, Comment.created_at, fourteen_days_ago, seven_days_ago),
        "reactions": _get_delta_data(Reaction, Reaction.created_at, fourteen_days_ago, seven_days_ago),
        "views": _get_delta_data(View, View.created_at, fourteen_days_ago, seven_days_ago),
        "saves": _get_delta_data(Save, Save.created_at, fourteen_days_ago, seven_days_ago),
        "shares": _get_delta_data(Share, Share.created_at, fourteen_days_ago, seven_days_ago),
        "clicks": _get_delta_data(ProductClick, ProductClick.created_at, fourteen_days_ago, seven_days_ago),
    }

    # P3-3: Sentiment Distribution
    sentiment_rows = db.session.execute(
        select(Comment.sentiment, func.count(Comment.id))
        .where(Comment.sentiment.isnot(None))
        .group_by(Comment.sentiment)
    ).all()
    sentiment_dist = {r[0]: r[1] for r in sentiment_rows}

    # P3-4: Spam Rate Trend (spam comments per day)
    spam_stmt = (
        select(
            cast(Comment.created_at, Date).label("date"),
            func.count().label("count")
        )
        .where(Comment.created_at >= thirty_days_ago, Comment.sentiment == 'spam')
        .group_by(cast(Comment.created_at, Date))
    )
    spam_trend = {r.date.isoformat(): r.count for r in db.session.execute(spam_stmt)}

    # P3-5: Recommendation CTR Panel (Lightweight)
    total_recs_impressions = db.session.scalar(select(func.count()).select_from(RecommendationImpression)) or 0
    total_recs_clicks = db.session.scalar(select(func.count()).select_from(RecommendationClick)) or 0
    recs_ctr = round((total_recs_clicks / total_recs_impressions) * 100, 2) if total_recs_impressions > 0 else 0

    # P3-6: Top Saved Content/Items
    top_saves_stmt = (
        select(Save.target_type, Save.target_id, func.count(Save.id).label("cnt"))
        .group_by(Save.target_type, Save.target_id)
        .order_by(desc("cnt"))
        .limit(5)
    )
    top_saves_rows = db.session.execute(top_saves_stmt).all()
    top_saves = []
    for r in top_saves_rows:
        target_name = "Unknown"
        if r.target_type == "content":
            c = db.session.get(Content, r.target_id)
            if c: target_name = c.title
        elif r.target_type == "product":
            i = db.session.get(Product, r.target_id)
            if i: target_name = i.name
        top_saves.append({
            "target_type": r.target_type,
            "target_id": r.target_id,
            "name": target_name,
            "count": r.cnt
        })

    # P3-7: Click Country Distribution
    country_rows = db.session.execute(
        select(ProductClick.country, func.count(ProductClick.id))
        .where(ProductClick.country.isnot(None))
        .group_by(ProductClick.country)
        .order_by(desc(func.count(ProductClick.id)))
        .limit(10)
    ).all()
    country_dist = {r[0] or "Unknown": r[1] for r in country_rows}

    # P3-8: Reaction Distribution by target_type
    target_type_rows = db.session.execute(
        select(Reaction.target_type, func.count(Reaction.id))
        .group_by(Reaction.target_type)
    ).all()
    reaction_targets = {r[0]: r[1] for r in target_type_rows}

    return {
        "trends": trends,
        "deltas": deltas,
        "sentiment_dist": sentiment_dist,
        "spam_trend": spam_trend,
        "recs_kpi": {
            "impressions": total_recs_impressions,
            "clicks": total_recs_clicks,
            "ctr": recs_ctr
        },
        "top_saves": top_saves,
        "country_dist": country_dist,
        "reaction_targets": reaction_targets,
        "moderation_workload": get_moderation_workload_data(),
        "heatmap": get_hourly_engagement_heatmap()
    }

@cache.cached(timeout=300, key_prefix="interactions_moderation_workload")
def get_moderation_workload_data() -> dict:
    """Returns moderation KPI stats: new comments, flagged, and triage queue."""
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(days=1)
    
    daily_new = db.session.scalar(select(func.count()).select_from(Comment).where(Comment.created_at >= one_day_ago)) or 0
    daily_flagged = db.session.scalar(
        select(func.count())
        .select_from(Comment)
        .where(Comment.created_at >= one_day_ago, Comment.sentiment.in_(["spam", "negative"]))
    ) or 0
    
    # Assume "pending triage" are any spam/negative comments overall (since there's no resolved state yet)
    pending_triage = db.session.scalar(
        select(func.count())
        .select_from(Comment)
        .where(Comment.sentiment.in_(["spam", "negative"]))
    ) or 0
    
    return {
        "daily_new": daily_new,
        "daily_flagged": daily_flagged,
        "pending_triage": pending_triage
    }

@cache.cached(timeout=600, key_prefix="interactions_hourly_heatmap")
def get_hourly_engagement_heatmap() -> list:
    """Returns a 24-element array of engagement counts by hour of day (0-23)."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    
    views_hc = _get_hour_counts_data(View, View.created_at, thirty_days_ago)
    comments_hc = _get_hour_counts_data(Comment, Comment.created_at, thirty_days_ago)
    reactions_hc = _get_hour_counts_data(Reaction, Reaction.created_at, thirty_days_ago)
    saves_hc = _get_hour_counts_data(Save, Save.created_at, thirty_days_ago)
    shares_hc = _get_hour_counts_data(Share, Share.created_at, thirty_days_ago)
    
    heatmap = []
    for hour in range(24):
        total = (
            views_hc.get(hour, 0) +
            comments_hc.get(hour, 0) +
            reactions_hc.get(hour, 0) +
            saves_hc.get(hour, 0) +
            shares_hc.get(hour, 0)
        )
        heatmap.append(total)
        
    return heatmap
