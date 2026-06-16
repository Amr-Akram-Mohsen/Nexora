from sqlalchemy import func, select, case, union_all
from datetime import datetime, timedelta, timezone
from app.core.extensions import db
from app.domains.interaction.models import View, Reaction, Comment, Save, ItemClick
from app.domains.content.models import Content
from app.domains.item.models import Item, ItemStoreLink, ItemVariant
from app.domains.taxonomy.models import Category, Brand, Topic
from app.domains.relationships import content_brands, content_topics
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

    # 2. Item Interactions
    item_interactions = _get_interaction_unions("item", start_b)
    add_stats(select(
        Item.category_id,
        func.count(case((item_interactions.c.created_at >= start_a, 1))).label("a"),
        func.count(case(((item_interactions.c.created_at >= start_b) & (item_interactions.c.created_at < start_a), 1))).label("b")
    ).join(item_interactions, item_interactions.c.target_id == Item.id).group_by(Item.category_id))

    # 3. Item Clicks
    add_stats(select(
        Item.category_id,
        func.count(case((ItemClick.created_at >= start_a, 1))).label("a"),
        func.count(case(((ItemClick.created_at >= start_b) & (ItemClick.created_at < start_a), 1))).label("b")
    ).select_from(ItemClick)
     .join(ItemStoreLink, ItemClick.item_store_link_id == ItemStoreLink.id)
     .join(ItemVariant, ItemStoreLink.variant_id == ItemVariant.id)
     .join(Item, ItemVariant.item_id == Item.id)
     .where(ItemClick.created_at >= start_b)
     .group_by(Item.category_id))

    return finalize_trend_stats(cat_stats)

def get_trending_brands_data():
    now = datetime.now(timezone.utc)
    start_a = now - timedelta(days=7)
    start_b = now - timedelta(days=14)

    brands = db.session.execute(select(Brand.id, Brand.name, Brand.slug)).all()
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
    add_stats(select(
        content_brands.c.brand_id,
        func.count(case((content_interactions.c.created_at >= start_a, 1))).label("a"),
        func.count(case(((content_interactions.c.created_at >= start_b) & (content_interactions.c.created_at < start_a), 1))).label("b")
    ).join(content_interactions, content_interactions.c.target_id == content_brands.c.content_id).group_by(content_brands.c.brand_id))

    # Item Interactions
    item_interactions = _get_interaction_unions("item", start_b)
    add_stats(select(
        Item.brand_id,
        func.count(case((item_interactions.c.created_at >= start_a, 1))).label("a"),
        func.count(case(((item_interactions.c.created_at >= start_b) & (item_interactions.c.created_at < start_a), 1))).label("b")
    ).join(item_interactions, item_interactions.c.target_id == Item.id).group_by(Item.brand_id))

    # Item Clicks
    add_stats(select(
        Item.brand_id,
        func.count(case((ItemClick.created_at >= start_a, 1))).label("a"),
        func.count(case(((ItemClick.created_at >= start_b) & (ItemClick.created_at < start_a), 1))).label("b")
    ).select_from(ItemClick)
     .join(ItemStoreLink, ItemClick.item_store_link_id == ItemStoreLink.id)
     .join(ItemVariant, ItemStoreLink.variant_id == ItemVariant.id)
     .join(Item, ItemVariant.item_id == Item.id)
     .where(ItemClick.created_at >= start_b)
     .group_by(Item.brand_id))

    return finalize_trend_stats(brand_stats)

def get_trending_topics_data():
    now = datetime.now(timezone.utc)
    start_a = now - timedelta(days=7)
    start_b = now - timedelta(days=14)

    topics = db.session.execute(select(Topic.id, Topic.name, Topic.slug)).all()
    topic_stats = {
        t.id: {"id": t.id, "name": t.name, "slug": t.slug, "period_a": 0, "period_b": 0}
        for t in topics
    }

    content_interactions = _get_interaction_unions("content", start_b)
    stmt = select(
        content_topics.c.topic_id,
        func.count(case((content_interactions.c.created_at >= start_a, 1))).label("a"),
        func.count(case(((content_interactions.c.created_at >= start_b) & (content_interactions.c.created_at < start_a), 1))).label("b")
    ).join(content_interactions, content_interactions.c.target_id == content_topics.c.content_id).group_by(content_topics.c.topic_id)

    for tid, a, b in db.session.execute(stmt):
        if tid in topic_stats:
            topic_stats[tid]["period_a"] += a or 0
            topic_stats[tid]["period_b"] += b or 0

    return finalize_trend_stats(topic_stats)
