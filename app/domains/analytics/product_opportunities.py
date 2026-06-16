from sqlalchemy import func, select, desc, case, cast, Integer
from functools import lru_cache
from app.core.extensions import db
from app.domains.interaction.models import View, Reaction, Comment, Save, ItemClick, RecommendationImpression, RecommendationClick
from app.domains.content.models import Content
from app.domains.item.models import Item, ItemStoreLink, ItemVariant
from app.domains.taxonomy.models import Category, Brand, Topic, IntentFacet
from app.domains.relationships import content_brands, content_topics
from app.domains.analytics.shared import (
    get_start_date,
    finalize_trend_stats,
    build_period_split_query,
    compute_quality_scores
)

def get_top_products_data(time_frame: str, limit: int = 5):
    start_date = get_start_date(time_frame)

    # 1. Most viewed products
    stmt_views = select(View.target_id, func.count(View.id).label("cnt")).where(View.target_type == "item")
    if start_date:
        stmt_views = stmt_views.where(View.created_at >= start_date)
    stmt_views = stmt_views.group_by(View.target_id).order_by(desc("cnt")).limit(limit)
    views_res = db.session.execute(stmt_views).all()

    # 2. Most clicked products
    stmt_clicks = (
        select(ItemVariant.item_id, func.count(ItemClick.id).label("cnt"))
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
        .join(ItemClick, ItemClick.item_store_link_id == ItemStoreLink.id)
    )
    if start_date:
        stmt_clicks = stmt_clicks.where(ItemClick.created_at >= start_date)
    stmt_clicks = stmt_clicks.group_by(ItemVariant.item_id).order_by(desc("cnt")).limit(limit)
    clicks_res = db.session.execute(stmt_clicks).all()

    # 3. Most saved products
    stmt_saves = select(Save.target_id, func.count(Save.id).label("cnt")).where(Save.target_type == "item")
    if start_date:
        stmt_saves = stmt_saves.where(Save.created_at >= start_date)
    stmt_saves = stmt_saves.group_by(Save.target_id).order_by(desc("cnt")).limit(limit)
    saves_res = db.session.execute(stmt_saves).all()

    # Gather all unique item IDs
    all_item_ids = set()
    for row in views_res + clicks_res + saves_res:
        all_item_ids.add(row[0])

    item_map = {}
    if all_item_ids:
        items = db.session.execute(select(Item).where(Item.id.in_(all_item_ids))).scalars().all()
        item_map = {item.id: item for item in items}

    def format_list(results):
        formatted = []
        for iid, count in results:
            item = item_map.get(iid)
            if item:
                formatted.append({
                    "id": iid,
                    "name": item.name,
                    "count": count
                })
        return formatted

    return {
        "most_viewed": format_list(views_res),
        "most_clicked": format_list(clicks_res),
        "most_saved": format_list(saves_res),
    }

def get_brand_opportunity_data():
    brands = db.session.execute(select(Brand.id, Brand.name)).all()
    brand_data = {b.id: {
        "name": b.name,
        "article_volume": 0,
        "product_volume": 0,
        "engagement": 0
    } for b in brands}

    art_vol_stmt = select(
        content_brands.c.brand_id,
        func.count(content_brands.c.content_id).label("count")
    ).group_by(content_brands.c.brand_id)
    for b_id, count in db.session.execute(art_vol_stmt).all():
        if b_id in brand_data:
            brand_data[b_id]["article_volume"] = count

    prod_vol_stmt = select(
        Item.brand_id,
        func.count(Item.id).label("count")
    ).group_by(Item.brand_id)
    for b_id, count in db.session.execute(prod_vol_stmt).all():
        if b_id in brand_data:
            brand_data[b_id]["product_volume"] = count

    brand_content_eng_stmt = select(
        content_brands.c.brand_id,
        func.sum(
            Content.view_count + Content.like_count + Content.dislike_count + Content.save_count + Content.comment_count
        ).label("eng")
    ).join(Content, Content.id == content_brands.c.content_id)\
     .group_by(content_brands.c.brand_id)
    for b_id, eng in db.session.execute(brand_content_eng_stmt).all():
        if b_id in brand_data:
            brand_data[b_id]["engagement"] += int(eng or 0)

    brand_prod_eng_stmt = select(
        Item.brand_id,
        func.sum(Item.view_count + Item.click_count + Item.save_count).label("eng")
    ).group_by(Item.brand_id)
    for b_id, eng in db.session.execute(brand_prod_eng_stmt).all():
        if b_id in brand_data:
            brand_data[b_id]["engagement"] += int(eng or 0)

    results = list(brand_data.values())
    if not results:
        return []

    avg_engagement = sum(b["engagement"] for b in results) / len(results)
    avg_articles = sum(b["article_volume"] for b in results) / len(results)

    for b in results:
        b["opportunity"] = b["engagement"] > avg_engagement and b["article_volume"] <= avg_articles
        if b["engagement"] > avg_engagement * 1.5:
            b["engagement_level"] = "High"
        elif b["engagement"] > avg_engagement * 0.5:
            b["engagement_level"] = "Medium"
        else:
            b["engagement_level"] = "Low"

    results.sort(key=lambda x: x["engagement"], reverse=True)
    return results