from sqlalchemy import func, select, desc
from app.core.extensions import db
from app.domains.distribution.models import DistributionPost, DistributionPlatform
from app.domains.content.models import Content
from app.domains.product.models import Product
from datetime import datetime, timezone, timedelta

def get_distribution_intelligence_data():
    now_utc = datetime.now(timezone.utc)
    
    total_content = db.session.scalar(select(func.count(Content.id)).where(Content.is_published == True)) or 0
    distributed_content = db.session.scalar(
        select(func.count(func.distinct(Content.id)))
        .join(DistributionPost, (DistributionPost.source_target_type == 'content') & (DistributionPost.source_target_id == Content.id))
        .where(Content.is_published == True, DistributionPost.status == 'published')
    ) or 0
    
    total_items = db.session.scalar(select(func.count(Product.id))) or 0
    distributed_items = db.session.scalar(
        select(func.count(func.distinct(Product.id)))
        .join(DistributionPost, (DistributionPost.source_target_type == 'product') & (DistributionPost.source_target_id == Product.id))
        .where(DistributionPost.status == 'published')
    ) or 0
    
    content_coverage = (distributed_content / total_content * 100) if total_content else 0
    item_coverage = (distributed_items / total_items * 100) if total_items else 0
    
    platform_stats = db.session.execute(
        select(
            DistributionPlatform.name,
            func.count(DistributionPost.id).label("post_count"),
            func.sum(DistributionPost.views_count).label("views"),
            func.sum(DistributionPost.likes_count).label("likes"),
            func.sum(DistributionPost.clicks_count).label("clicks"),
            func.sum(DistributionPost.shares_count).label("shares")
        )
        .join(DistributionPlatform)
        .where(DistributionPost.status == 'published')
        .group_by(DistributionPlatform.name)
    ).all()
    
    platforms = []
    for r in platform_stats:
        v = r.views or 0
        l = r.likes or 0
        c = r.clicks or 0
        s = r.shares or 0
        engagement_index = (l * 2) + (c * 5) + (s * 10) + (v * 0.1)
        avg_engagement = engagement_index / r.post_count if r.post_count else 0
        
        platforms.append({
            "platform": r.name,
            "post_count": r.post_count,
            "engagement_index": round(engagement_index, 1),
            "avg_engagement_per_post": round(avg_engagement, 1)
        })
        
    platforms.sort(key=lambda x: x["engagement_index"], reverse=True)
    
    posts_with_dates = db.session.execute(
        select(DistributionPost.publish_date, Content.created_at)
        .select_from(DistributionPost)
        .join(Content, (DistributionPost.source_target_type == 'content') & (DistributionPost.source_target_id == Content.id))
        .where(DistributionPost.status == 'published', DistributionPost.publish_date != None)
    ).all()
    
    deltas = []
    for pub_date, c_date in posts_with_dates:
        if pub_date and c_date:
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            if c_date.tzinfo is None:
                c_date = c_date.replace(tzinfo=timezone.utc)
            delta = (pub_date - c_date).total_seconds()
            if delta > 0:
                deltas.append(delta)
                
    time_to_dist_hours = (sum(deltas) / len(deltas)) / 3600 if deltas else 0
    
    return {
        "coverage": {
            "content_coverage": round(content_coverage, 1),
            "item_coverage": round(item_coverage, 1),
            "total_content": total_content,
            "distributed_content": distributed_content,
            "total_items": total_items,
            "distributed_items": distributed_items
        },
        "platforms": platforms,
        "time_to_distribution_hours": round(time_to_dist_hours, 1)
    }


def get_social_distribution_summary():
    now_utc = datetime.now(timezone.utc)
    return {
        "draft": db.session.scalar(select(func.count()).select_from(DistributionPost).where(DistributionPost.status == "draft")),
        "scheduled": db.session.scalar(select(func.count()).select_from(DistributionPost).where(DistributionPost.status == "scheduled")),
        "published": db.session.scalar(select(func.count()).select_from(DistributionPost).where(DistributionPost.status == "published")),
        "overdue": db.session.scalar(select(func.count()).select_from(DistributionPost).where(DistributionPost.status == "scheduled", DistributionPost.publish_date < now_utc)),
    }


def get_overview_kpis():
    now_utc = datetime.now(timezone.utc)
    stats = {
        "total_posts": db.session.scalar(select(func.count()).select_from(DistributionPost)),
        "published": db.session.scalar(select(func.count()).select_from(DistributionPost).where(DistributionPost.status == "published")),
        "scheduled": db.session.scalar(select(func.count()).select_from(DistributionPost).where(DistributionPost.status == "scheduled")),
        "drafts": db.session.scalar(select(func.count()).select_from(DistributionPost).where(DistributionPost.status == "draft")),
        "overdue": db.session.scalar(select(func.count()).select_from(DistributionPost).where(DistributionPost.status == "scheduled", DistributionPost.publish_date < now_utc)),
        "total_views": db.session.scalar(select(func.sum(DistributionPost.views_count)).select_from(DistributionPost)) or 0,
        "total_engagement": db.session.scalar(
            select(
                func.sum(
                    DistributionPost.views_count + 
                    (DistributionPost.likes_count * 2) + 
                    (DistributionPost.shares_count * 3) + 
                    (DistributionPost.clicks_count * 1.5)
                )
            ).select_from(DistributionPost)
        ) or 0
    }
    return stats


def get_health_alerts():
    now_utc = datetime.now(timezone.utc)
    stale_threshold = now_utc - timedelta(days=7)
    
    overdue_count = db.session.scalar(
        select(func.count()).select_from(DistributionPost)
        .where(DistributionPost.status == "scheduled", DistributionPost.publish_date < now_utc)
    ) or 0
    
    stale_drafts_count = db.session.scalar(
        select(func.count()).select_from(DistributionPost)
        .where(DistributionPost.status == "draft", DistributionPost.updated_at < stale_threshold)
    ) or 0
    
    no_url_published_count = db.session.scalar(
        select(func.count()).select_from(DistributionPost)
        .where(DistributionPost.status == "published", DistributionPost.external_url.is_(None))
    ) or 0
    
    alerts = []
    if overdue_count > 0:
        alerts.append({
            "type": "danger",
            "icon": "⚠️",
            "title": "Overdue Posts",
            "message": f"There are {overdue_count} scheduled posts that have passed their target publish date."
        })
    if stale_drafts_count >= 5:
        alerts.append({
            "type": "warning",
            "icon": "📝",
            "title": "Stale Drafts",
            "message": f"You have {stale_drafts_count} drafts that haven't been updated in over 7 days."
        })
    if no_url_published_count > 0:
        alerts.append({
            "type": "warning",
            "icon": "🔗",
            "title": "Missing URLs",
            "message": f"{no_url_published_count} published posts are missing external verifiable URLs."
        })
    return alerts


def get_coverage_analytics():
    total_content = db.session.scalar(
        select(func.count()).select_from(Content)
        .where(Content.is_active == True, Content.is_published == True)
    ) or 0
    
    distributed_content = db.session.scalar(
        select(func.count(func.distinct(Content.id))).select_from(Content)
        .join(DistributionPost, (
            (DistributionPost.source_target_type == 'content') &
            (DistributionPost.source_target_id == Content.id)
        ))
        .where(Content.is_active == True, Content.is_published == True, DistributionPost.status == 'published')
    ) or 0
    
    total_items = db.session.scalar(select(func.count()).select_from(Product)) or 0
    
    distributed_items = db.session.scalar(
        select(func.count(func.distinct(Product.id))).select_from(Product)
        .join(DistributionPost, (
            (DistributionPost.source_target_type == 'product') &
            (DistributionPost.source_target_id == Product.id)
        ))
        .where(DistributionPost.status == 'published')
    ) or 0
    
    content_coverage_pct = (distributed_content / total_content * 100) if total_content > 0 else 0
    item_coverage_pct = (distributed_items / total_items * 100) if total_items > 0 else 0
    
    return {
        "content": {
            "total": total_content,
            "distributed": distributed_content,
            "percentage": round(content_coverage_pct, 1)
        },
        "product": {
            "total": total_items,
            "distributed": distributed_items,
            "percentage": round(item_coverage_pct, 1)
        }
    }


def get_platform_performance():
    query = (
        select(
            DistributionPlatform.name.label("platform_name"),
            func.count(DistributionPost.id).label("post_count"),
            func.sum(DistributionPost.views_count).label("total_views"),
            func.sum(DistributionPost.likes_count).label("total_likes"),
            func.sum(DistributionPost.clicks_count).label("total_clicks"),
            func.sum(DistributionPost.shares_count).label("total_shares")
        )
        .join(DistributionPlatform)
        .where(DistributionPost.status == 'published')
        .group_by(DistributionPlatform.name)
        .order_by(desc(func.sum(DistributionPost.views_count)))
    )
    
    results = db.session.execute(query).all()
    
    platforms_data = []
    for row in results:
        v = row.total_views or 0
        l = row.total_likes or 0
        c = row.total_clicks or 0
        s = row.total_shares or 0
        engagement = (l * 2) + (c * 5) + (s * 10) + (v * 0.1)
        
        platforms_data.append({
            "name": row.platform_name,
            "post_count": row.post_count,
            "views": v,
            "likes": l,
            "clicks": c,
            "shares": s,
            "engagement": engagement
        })
        
    return platforms_data
