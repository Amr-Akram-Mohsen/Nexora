from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select, cast, Date
from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.taxonomy.models import Category, Source
from app.domains.item.models import Item
from app.domains.user.models import User
from app.domains.interaction.service.query import get_interactions_breakdown
from app.domains.interaction.models import Share



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

def get_admin_top_items():
    rows = db.session.execute(
        select(Item.id, Item.name, Item.item_type, Item.click_count, Item.rating)
        .order_by(Item.click_count.desc())
        .limit(5)
    ).mappings().all()
    return [{
        "id":          r["id"],
        "name":        r["name"],
        "item_type":   r["item_type"],
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
