# app/admin/stats.py
from flask import Blueprint, jsonify
from app.core.extensions import db
from app.domains.content.models import Content, Article, Video, Post
from app.domains.taxonomy.models import Category, Section, Source
from app.domains.relationships import ArticleSource
from app.domains.item.models import Item
from app.domains.user.models import User
from app.domains.interaction.service.query import get_interactions_breakdown, get_reaction_stats
from app.core.decorators import admin_required
from sqlalchemy import func, select
from datetime import datetime, timedelta

bp = Blueprint("api_dashboard", __name__, url_prefix="/admin/dashboard")

# @bp.before_request
# @admin_required
# def require_admin():
#     """Ensure all stats/dashboard endpoints require admin privilege."""
#     pass


@bp.route("/stats", methods=["GET"])
def dashboard_stats():
    """Enhanced dashboard metrics, aggregates, distributions, and trends."""
    # Unified Interaction Stats
    breakdown = get_interactions_breakdown()   # {comments, reactions, views, saves, shares, clicks}
    reaction_stats = get_reaction_stats()      # {likes, dislikes}
    total_interactions = sum(breakdown.values())

    # Catalog Grand Totals
    contents_count = db.session.query(Content.id).count()
    items_count = db.session.query(Item.id).count()
    users_count = db.session.query(User.id).count()

    # Active / Inactive distribution
    active_contents = db.session.query(Content.id).filter(Content.is_active == True).count()
    inactive_contents = db.session.query(Content.id).filter(Content.is_active == False).count()
    
    # Review queue (Draft contents waiting moderation / publishing)
    review_queue_count = db.session.query(Content.id).filter(Content.is_published == False).count()

    # Content breakdown by type
    by_type_rows = db.session.query(Content.object_type, func.count(Content.id)).group_by(Content.object_type).all()
    by_type = {r[0]: r[1] for r in by_type_rows}
    
    # Format to ensure all types exist
    type_distribution = {
        "article": by_type.get("article", 0),
        "video": by_type.get("video", 0),
        "post": by_type.get("post", 0)
    }

    # Content count by active categories (Top 6)
    by_category_rows = db.session.query(
        Category.name, func.count(Content.id)
    ).join(Content.category).group_by(Category.name).order_by(func.count(Content.id).desc()).limit(6).all()
    
    category_distribution = [{"name": r[0], "count": r[1]} for r in by_category_rows]

    # Content count by top sources (Top 6 including YT / Reddit)
    source_distribution = []
    
    # 1. YouTube count
    yt_count = type_distribution["video"]
    if yt_count > 0:
        source_distribution.append({"name": "YouTube", "count": yt_count})
        
    # 2. Reddit count
    reddit_count = type_distribution["post"]
    if reddit_count > 0:
        source_distribution.append({"name": "Reddit", "count": reddit_count})

    # 3. Dynamic DB sources count
    db_source_rows = db.session.query(
        Source.name, func.count(Content.id)
    ).select_from(Content).join(
        ArticleSource, ArticleSource.article_id == Content.object_id
    ).join(
        Source, Source.id == ArticleSource.source_id
    ).filter(
        Content.object_type == "article"
    ).group_by(Source.name).order_by(func.count(Content.id).desc()).limit(6).all()
    
    for r in db_source_rows:
        source_distribution.append({"name": r[0], "count": r[1]})

    # Sort sources by count descending
    source_distribution = sorted(source_distribution, key=lambda x: x["count"], reverse=True)[:6]

    # Ingestion Growth Trends (Last 7 Days)
    growth_trends = []
    today = datetime.utcnow().date()
    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        day_start = datetime.combine(day_date, datetime.min.time())
        day_end = datetime.combine(day_date, datetime.max.time())
        
        count = db.session.query(Content.id).filter(
            Content.published_at >= day_start,
            Content.published_at <= day_end
        ).count()
        
        growth_trends.append({
            "date": day_date.strftime("%b %d"),
            "count": count
        })

    # Recently Ingested items (Latest 5)
    recent_rows = db.session.query(Content).order_by(Content.ingested_at.desc()).limit(5).all()
    recent_ingested = []
    for r in recent_rows:
        time_diff = datetime.utcnow() - r.ingested_at
        time_str = "Recently"
        if time_diff.days > 0:
            time_str = f"{time_diff.days}d ago"
        elif time_diff.seconds >= 3600:
            time_str = f"{time_diff.seconds // 3600}h ago"
        elif time_diff.seconds >= 60:
            time_str = f"{time_diff.seconds // 60}m ago"
        else:
            time_str = "Just now"

        recent_ingested.append({
            "id": r.id,
            "title": r.title or f"Untitled ({r.object_type})",
            "type": r.object_type,
            "time": time_str
        })

    return jsonify({
        "contents_count": contents_count,
        "items_count": items_count,
        "users_count": users_count,
        "active_contents": active_contents,
        "inactive_contents": inactive_contents,
        "review_queue_count": review_queue_count,
        "by_type": type_distribution,
        "by_category": category_distribution,
        "by_source": source_distribution,
        "growth_trends": growth_trends,
        "recent_ingested": recent_ingested,
        "interactions": {
            "total":     total_interactions,
            "views":     breakdown.get("views", 0),
            "comments":  breakdown.get("comments", 0),
            "reactions": breakdown.get("reactions", 0),
            "saves":     breakdown.get("saves", 0),
            "shares":    breakdown.get("shares", 0),
            "clicks":    breakdown.get("clicks", 0),
            "likes":     reaction_stats.get("likes", 0),
            "dislikes":  reaction_stats.get("dislikes", 0),
        }
    })


@bp.route("/top-contents", methods=["GET"])
def top_contents():
    """Top 5 content items by view count for the overview panel."""
    rows = db.session.execute(
        select(Content.id, Content.title, Content.object_type, Content.view_count)
        .order_by(Content.view_count.desc())
        .limit(5)
    ).mappings().all()
    return jsonify([{
        "id": r["id"],
        "title": r["title"] or f"{r['object_type'].capitalize()} #{r['id']}",
        "type": r["object_type"],
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
        "id": r["id"],
        "name": r["name"],
        "item_type": r["item_type"],
        "click_count": r["click_count"] or 0,
        "rating": r["rating"],
    } for r in rows])
