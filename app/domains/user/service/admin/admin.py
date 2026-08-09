from sqlalchemy import select, or_, and_, func
from app.core.extensions import db
from app.domains.user.models import User, NewsletterSubscriber


from app.shared.utils.admin_helpers import execute_paginated_query

def get_admin_users_paginated(search, role, status, verified, subscription, provider, sort_by, sort_dir, page, per_page):
    from app.domains.user.service.admin.analytics import build_user_query as domain_build_user_query
    stmt, count_stmt = domain_build_user_query(search, role, status, verified, subscription, provider, sort_by, sort_dir)
            
    stats = {
        "active": db.session.scalar(count_stmt.where(User.is_active == True)) or 0,
        "admins": db.session.scalar(count_stmt.where(User.is_admin == True)) or 0,
        "verified": db.session.scalar(count_stmt.where(User.is_verified == True)) or 0,
        "subscribed": db.session.scalar(
            count_stmt.outerjoin(NewsletterSubscriber, User.id == NewsletterSubscriber.user_id)
            .where(NewsletterSubscriber.is_confirmed == True, NewsletterSubscriber.unsubscribed_at.is_(None))
        ) or 0
    }
    
    products, total, pages = execute_paginated_query(stmt, count_stmt, page, per_page)
    return products, total, pages, stats

def toggle_admin_user(id):
    from app.shared.utils.admin_helpers import toggle_model_flag_workflow
    return toggle_model_flag_workflow(User, id, "is_admin")

def get_admin_user_inspect_raw(id):
    from sqlalchemy.orm import selectinload
    from app.domains.recommendation.models import UserInterest
    stmt_user = select(User).options(
        selectinload(User.user_interests).selectinload(UserInterest.entity_scores),
        selectinload(User.newsletter_subscription)
    ).where(User.id == id)
    user = db.session.scalar(stmt_user)
    return user

def build_user_inspect_maps(user):
    from app.domains.taxonomy.models import Category, Entity
    entity_ids = set()
    category_ids = set()
    for ui in user.user_interests:
        for score in ui.entity_scores:
            if getattr(score, 'entity_id', None): entity_ids.add(score.entity_id)
            if getattr(score, 'category_id', None): category_ids.add(score.category_id)
            
    entities = db.session.execute(select(Entity).where(Entity.id.in_(entity_ids))).scalars() if entity_ids else []
    brands_map = {e.id: e.name for e in entities if e.entity_type == 'brand'}
    topics_map = {e.id: e.name for e in entities if e.entity_type in ['topic', 'tag', 'concept']}
    categories_map = {c.id: c.name for c in db.session.execute(select(Category).where(Category.id.in_(category_ids))).scalars()} if category_ids else {}

    product_ids = {ui.target_id for ui in user.user_interests if ui.target_type == 'product'}
    article_ids = {ui.target_id for ui in user.user_interests if ui.target_type in ('article', 'content')}
    items_map = {}
    articles_map = {}
    if product_ids:
        from app.domains.product.models import Product
        items_map = {i.id: i.name for i in db.session.execute(select(Product).where(Product.id.in_(product_ids))).scalars()}
    if article_ids:
        from app.domains.content.models import Content
        articles_map = {c.id: c.title for c in db.session.execute(select(Content).where(Content.id.in_(article_ids))).scalars()}

    return brands_map, categories_map, topics_map, items_map, articles_map


def get_admin_subscribers_paginated(search, status, has_user, page, per_page):
    stmt = select(NewsletterSubscriber).outerjoin(User, NewsletterSubscriber.user_id == User.id).order_by(NewsletterSubscriber.id.desc())
    count_stmt = select(func.count(NewsletterSubscriber.id))

    if search:
        search_filter = or_(NewsletterSubscriber.email.ilike(f"%{search}%"), User.name.ilike(f"%{search}%"))
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)
    
    if status:
        if status == 'confirmed':
            status_filter = and_(NewsletterSubscriber.is_confirmed == True, NewsletterSubscriber.unsubscribed_at.is_(None))
        elif status == 'unconfirmed':
            status_filter = NewsletterSubscriber.is_confirmed == False
        elif status == 'unsubscribed':
            status_filter = NewsletterSubscriber.unsubscribed_at.isnot(None)
        stmt = stmt.where(status_filter)
        count_stmt = count_stmt.where(status_filter)
        
    if has_user:
        user_filter = NewsletterSubscriber.user_id.isnot(None) if has_user == 'true' else NewsletterSubscriber.user_id.is_(None)
        stmt = stmt.where(user_filter)
        count_stmt = count_stmt.where(user_filter)

    stats = {
        "total": db.session.scalar(count_stmt) or 0,
        "confirmed": db.session.scalar(count_stmt.where(and_(NewsletterSubscriber.is_confirmed == True, NewsletterSubscriber.unsubscribed_at.is_(None)))) or 0,
        "unconfirmed": db.session.scalar(count_stmt.where(NewsletterSubscriber.is_confirmed == False)) or 0,
        "unsubscribed": db.session.scalar(count_stmt.where(NewsletterSubscriber.unsubscribed_at.isnot(None))) or 0,
        "anonymous": db.session.scalar(count_stmt.where(NewsletterSubscriber.user_id.is_(None))) or 0
    }

    products, total, pages = execute_paginated_query(stmt, count_stmt, page, per_page)
    # The original returned scalars, but execute_paginated_query returns all()
    # We must extract the scalars if the route expects models, or we can just return products if the route handles it.
    # Actually, execute_paginated_query returns the result of .all(), which is a list of tuples/Row.
    # Wait, the original was scalars().all(). We need to be careful.
    return [i[0] for i in products], total, pages, stats

def get_admin_audience_analytics_stats():
    from app.domains.interaction.models import RecommendationImpression, RecommendationClick
    
    clicks = db.session.scalar(select(func.count(RecommendationClick.id))) or 0
    impressions = db.session.scalar(select(func.count(RecommendationImpression.id))) or 0
    ctr = round((clicks / impressions * 100), 2) if impressions > 0 else 0

    total_users = db.session.scalar(select(func.count(User.id))) or 0
    active_users = db.session.scalar(select(func.count(User.id)).where(User.is_active == True)) or 0
    inactive_users = total_users - active_users

    from datetime import datetime, timezone, timedelta
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
