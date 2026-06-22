from sqlalchemy import func, select, desc
from app.core.extensions import db
from app.domains.distribution.models import DistributionPost, DistributionPlatform
from app.domains.content.models import Content
from app.domains.item.models import Item
from datetime import datetime, timezone, timedelta

def get_distribution_intelligence_data():
    now_utc = datetime.now(timezone.utc)
    
    total_content = db.session.scalar(select(func.count(Content.id)).where(Content.is_published == True)) or 0
    distributed_content = db.session.scalar(
        select(func.count(func.distinct(Content.id)))
        .join(DistributionPost, (DistributionPost.source_target_type == 'content') & (DistributionPost.source_target_id == Content.id))
        .where(Content.is_published == True, DistributionPost.status == 'published')
    ) or 0
    
    total_items = db.session.scalar(select(func.count(Item.id))) or 0
    distributed_items = db.session.scalar(
        select(func.count(func.distinct(Item.id)))
        .join(DistributionPost, (DistributionPost.source_target_type == 'item') & (DistributionPost.source_target_id == Item.id))
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
