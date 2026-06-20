from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select, cast, Date, desc, extract
from app.core.extensions import db, cache
from app.domains.interaction.models import Comment, Reaction, View, Save, Share, ItemClick, RecommendationImpression, RecommendationClick
from app.domains.content.models import Content
from app.domains.item.models import Item

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

    # Helper: Get 30-day trend
    def get_trend(model, date_col):
        stmt = (
            select(
                cast(date_col, Date).label("date"),
                func.count().label("count")
            )
            .where(date_col >= thirty_days_ago)
            .group_by(cast(date_col, Date))
        )
        return {r.date.isoformat(): r.count for r in db.session.execute(stmt)}

    trends = {
        "comments": get_trend(Comment, Comment.created_at),
        "reactions": get_trend(Reaction, Reaction.created_at),
        "views": get_trend(View, View.created_at),
        "saves": get_trend(Save, Save.created_at),
        "shares": get_trend(Share, Share.created_at),
        "clicks": get_trend(ItemClick, ItemClick.created_at),
    }

    # Helper: Get rolling 7-day delta (+N%)
    def get_delta(model, date_col):
        current_7 = db.session.scalar(select(func.count()).select_from(model).where(date_col >= seven_days_ago)) or 0
        prev_7 = db.session.scalar(select(func.count()).select_from(model).where(date_col >= fourteen_days_ago, date_col < seven_days_ago)) or 0
        if prev_7 == 0:
            return {"current": current_7, "prev": prev_7, "delta": 100 if current_7 > 0 else 0}
        return {"current": current_7, "prev": prev_7, "delta": round(((current_7 - prev_7) / prev_7) * 100, 1)}

    deltas = {
        "comments": get_delta(Comment, Comment.created_at),
        "reactions": get_delta(Reaction, Reaction.created_at),
        "views": get_delta(View, View.created_at),
        "saves": get_delta(Save, Save.created_at),
        "shares": get_delta(Share, Share.created_at),
        "clicks": get_delta(ItemClick, ItemClick.created_at),
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
        elif r.target_type == "item":
            i = db.session.get(Item, r.target_id)
            if i: target_name = i.name
        top_saves.append({
            "target_type": r.target_type,
            "target_id": r.target_id,
            "name": target_name,
            "count": r.cnt
        })

    # P3-7: Click Country Distribution
    country_rows = db.session.execute(
        select(ItemClick.country, func.count(ItemClick.id))
        .where(ItemClick.country.isnot(None))
        .group_by(ItemClick.country)
        .order_by(desc(func.count(ItemClick.id)))
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
    
    # PostgreSQL uses EXTRACT(hour from date_col)
    # Cast to integer to get 0-23
    def get_hour_counts(model, date_col):
        stmt = (
            select(
                cast(extract('hour', date_col), db.Integer).label("hour"),
                func.count().label("cnt")
            )
            .where(date_col >= thirty_days_ago)
            .group_by("hour")
        )
        return {r.hour: r.cnt for r in db.session.execute(stmt)}

    views_hc = get_hour_counts(View, View.created_at)
    comments_hc = get_hour_counts(Comment, Comment.created_at)
    reactions_hc = get_hour_counts(Reaction, Reaction.created_at)
    saves_hc = get_hour_counts(Save, Save.created_at)
    shares_hc = get_hour_counts(Share, Share.created_at)
    
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
