from sqlalchemy import func, select, case, union_all
from datetime import datetime, timedelta, timezone
from app.core.extensions import db
from app.domains.interaction.models import View, Reaction, Comment, Save, ProductClick
from app.domains.content.models import Content
from app.domains.product.models import Product, ProductStoreLink, ProductVariant
from app.domains.taxonomy.models import Category, Brand, Entity
from app.domains.relationships import ContentEntity
from app.domains.analytics.shared import finalize_trend_stats

def _get_interaction_unions(target_type, start_date):
    """Helper to union all interaction tables for a specific target type."""
    views = select(View.target_id, View.created_at).where(View.target_type == target_type, View.created_at >= start_date)
    reactions = select(Reaction.target_id, Reaction.created_at).where(Reaction.target_type == target_type, Reaction.created_at >= start_date)
    comments = select(Comment.target_id, Comment.created_at).where(Comment.target_type == target_type, Comment.created_at >= start_date)
    saves = select(Save.target_id, Save.created_at).where(Save.target_type == target_type, Save.created_at >= start_date)
    return union_all(views, reactions, comments, saves).subquery()

def get_trending_categories_data():
    now = datetime.now(timezone.utc)
    start_a = now - timedelta(days=7)
    start_b = now - timedelta(days=14)

    categories = db.session.execute(select(Category.id, Category.name, Category.slug)).all()
    cat_stats = {
        c.id: {"id": c.id, "name": c.name, "slug": c.slug, "period_a": 0, "period_b": 0}
        for c in categories
    }

    def add_stats(stmt):
        for cid, a, b in db.session.execute(stmt):
            if cid in cat_stats:
                cat_stats[cid]["period_a"] += a or 0
                cat_stats[cid]["period_b"] += b or 0

    # 1. Content Interactions
    content_interactions = _get_interaction_unions("content", start_b)
    add_stats(select(
        Content.category_id,
        func.count(case((content_interactions.c.created_at >= start_a, 1))).label("a"),
        func.count(case(((content_interactions.c.created_at >= start_b) & (content_interactions.c.created_at < start_a), 1))).label("b")
    ).join(content_interactions, content_interactions.c.target_id == Content.id).group_by(Content.category_id))

    # 2. Product Interactions
    item_interactions = _get_interaction_unions("product", start_b)
    add_stats(select(
        Product.category_id,
        func.count(case((item_interactions.c.created_at >= start_a, 1))).label("a"),
        func.count(case(((item_interactions.c.created_at >= start_b) & (item_interactions.c.created_at < start_a), 1))).label("b")
    ).join(item_interactions, item_interactions.c.target_id == Product.id).group_by(Product.category_id))

    # 3. Product Clicks
    add_stats(select(
        Product.category_id,
        func.count(case((ProductClick.created_at >= start_a, 1))).label("a"),
        func.count(case(((ProductClick.created_at >= start_b) & (ProductClick.created_at < start_a), 1))).label("b")
    ).select_from(ProductClick)
     .join(ProductStoreLink, ProductClick.product_store_link_id == ProductStoreLink.id)
     .join(ProductVariant, ProductStoreLink.variant_id == ProductVariant.id)
     .join(Product, ProductVariant.product_id == Product.id)
     .where(ProductClick.created_at >= start_b)
     .group_by(Product.category_id))

    return finalize_trend_stats(cat_stats)

def get_trending_brands_data():
    now = datetime.now(timezone.utc)
    start_a = now - timedelta(days=7)
    start_b = now - timedelta(days=14)

    from sqlalchemy import or_
    brands = db.session.execute(
        select(Entity.id, Entity.name, Entity.slug)
        .where(or_(Entity.entity_type == "brand", Entity.entity_type == "organization"))
    ).all()
    brand_stats = {
        b.id: {"id": b.id, "name": b.name, "slug": b.slug, "period_a": 0, "period_b": 0}
        for b in brands
    }

    def add_stats(stmt):
        for bid, a, b in db.session.execute(stmt):
            if bid in brand_stats:
                brand_stats[bid]["period_a"] += a or 0
                brand_stats[bid]["period_b"] += b or 0

    # Content Interactions
    content_interactions = _get_interaction_unions("content", start_b)
    brand_ids = list(brand_stats.keys()) if brand_stats else [0]
    add_stats(select(
        ContentEntity.entity_id,
        func.count(case((content_interactions.c.created_at >= start_a, 1))).label("a"),
        func.count(case(((content_interactions.c.created_at >= start_b) & (content_interactions.c.created_at < start_a), 1))).label("b")
    ).join(content_interactions, content_interactions.c.target_id == ContentEntity.content_id)
     .where(ContentEntity.entity_id.in_(brand_ids))
     .group_by(ContentEntity.entity_id))

    # Product Interactions (Mapping Product.brand_id -> Entity.id via slug)
    item_interactions = _get_interaction_unions("product", start_b)
    add_stats(select(
        Entity.id,
        func.count(case((item_interactions.c.created_at >= start_a, 1))).label("a"),
        func.count(case(((item_interactions.c.created_at >= start_b) & (item_interactions.c.created_at < start_a), 1))).label("b")
    ).select_from(item_interactions)
     .join(Product, item_interactions.c.target_id == Product.id)
     .join(Brand, Brand.id == Product.brand_id)
     .join(Entity, Entity.slug == Brand.slug)
     .group_by(Entity.id))

    # Product Clicks
    add_stats(select(
        Entity.id,
        func.count(case((ProductClick.created_at >= start_a, 1))).label("a"),
        func.count(case(((ProductClick.created_at >= start_b) & (ProductClick.created_at < start_a), 1))).label("b")
    ).select_from(ProductClick)
     .join(ProductStoreLink, ProductClick.product_store_link_id == ProductStoreLink.id)
     .join(ProductVariant, ProductStoreLink.variant_id == ProductVariant.id)
     .join(Product, ProductVariant.product_id == Product.id)
     .join(Brand, Brand.id == Product.brand_id)
     .join(Entity, Entity.slug == Brand.slug)
     .where(ProductClick.created_at >= start_b)
     .group_by(Entity.id))

    return finalize_trend_stats(brand_stats)

def get_trending_topics_data():
    now = datetime.now(timezone.utc)
    start_a = now - timedelta(days=7)
    start_b = now - timedelta(days=14)

    topics = db.session.execute(
        select(Entity.id, Entity.name, Entity.slug)
        .where(Entity.entity_type.in_(["tag", "concept", "topic"]))
    ).all()
    topic_stats = {
        t.id: {"id": t.id, "name": t.name, "slug": t.slug, "period_a": 0, "period_b": 0}
        for t in topics
    }

    content_interactions = _get_interaction_unions("content", start_b)
    topic_ids = list(topic_stats.keys()) if topic_stats else [0]
    stmt = select(
        ContentEntity.entity_id,
        func.count(case((content_interactions.c.created_at >= start_a, 1))).label("a"),
        func.count(case(((content_interactions.c.created_at >= start_b) & (content_interactions.c.created_at < start_a), 1))).label("b")
    ).join(content_interactions, content_interactions.c.target_id == ContentEntity.content_id)\
     .where(ContentEntity.entity_id.in_(topic_ids))\
     .group_by(ContentEntity.entity_id)

    for tid, a, b in db.session.execute(stmt):
        if tid in topic_stats:
            topic_stats[tid]["period_a"] += a or 0
            topic_stats[tid]["period_b"] += b or 0

    return finalize_trend_stats(topic_stats)
