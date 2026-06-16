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

def get_top_content_data(time_frame: str, limit: int = 5):
    start_date = get_start_date(time_frame)

    # 1. Most viewed content
    stmt_views = select(View.target_id, func.count(View.id).label("cnt")).where(View.target_type == "content")
    if start_date:
        stmt_views = stmt_views.where(View.created_at >= start_date)
    stmt_views = stmt_views.group_by(View.target_id).order_by(desc("cnt")).limit(limit)
    views_res = db.session.execute(stmt_views).all()

    # 2. Most reacted content
    stmt_reactions = select(Reaction.target_id, func.count(Reaction.id).label("cnt")).where(Reaction.target_type == "content")
    if start_date:
        stmt_reactions = stmt_reactions.where(Reaction.created_at >= start_date)
    stmt_reactions = stmt_reactions.group_by(Reaction.target_id).order_by(desc("cnt")).limit(limit)
    reactions_res = db.session.execute(stmt_reactions).all()

    # 3. Most commented content
    stmt_comments = select(Comment.target_id, func.count(Comment.id).label("cnt")).where(Comment.target_type == "content")
    if start_date:
        stmt_comments = stmt_comments.where(Comment.created_at >= start_date)
    stmt_comments = stmt_comments.group_by(Comment.target_id).order_by(desc("cnt")).limit(limit)
    comments_res = db.session.execute(stmt_comments).all()

    # 4. Most saved content
    stmt_saves = select(Save.target_id, func.count(Save.id).label("cnt")).where(Save.target_type == "content")
    if start_date:
        stmt_saves = stmt_saves.where(Save.created_at >= start_date)
    stmt_saves = stmt_saves.group_by(Save.target_id).order_by(desc("cnt")).limit(limit)
    saves_res = db.session.execute(stmt_saves).all()

    # Gather all unique content IDs
    all_content_ids = set()
    for row in views_res + reactions_res + comments_res + saves_res:
        all_content_ids.add(row[0])

    content_map = {}
    if all_content_ids:
        contents = db.session.execute(select(Content).where(Content.id.in_(all_content_ids))).scalars().all()
        content_map = {c.id: c for c in contents}

    def format_list(results):
        formatted = []
        for cid, count in results:
            content = content_map.get(cid)
            if content:
                formatted.append({
                    "id": cid,
                    "title": content.title or f"Content #{cid}",
                    "type": content.object_type,
                    "count": count
                })
        return formatted

    return {
        "most_viewed": format_list(views_res),
        "most_reacted": format_list(reactions_res),
        "most_commented": format_list(comments_res),
        "most_saved": format_list(saves_res),
    }

def get_content_opportunities():
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    start_30d = now - timedelta(days=30)

    categories = db.session.execute(select(Category.id, Category.name)).all()
    cat_map = {c.id: {"id": c.id, "name": c.name, "demand": 0, "content_count": 0} for c in categories}

    stmt = select(Item.category_id, func.count(View.id))\
        .join(View, (View.target_id == Item.id) & (View.target_type == "item"))\
        .where(View.created_at >= start_30d)\
        .group_by(Item.category_id)
    for cid, cnt in db.session.execute(stmt):
        if cid in cat_map:
            cat_map[cid]["demand"] += cnt or 0

    stmt = select(Item.category_id, func.count(ItemClick.id))\
        .join(ItemVariant, ItemVariant.item_id == Item.id)\
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)\
        .join(ItemClick, ItemClick.item_store_link_id == ItemStoreLink.id)\
        .where(ItemClick.created_at >= start_30d)\
        .group_by(Item.category_id)
    for cid, cnt in db.session.execute(stmt):
        if cid in cat_map:
            cat_map[cid]["demand"] += cnt or 0

    stmt = select(Item.category_id, func.count(Save.id))\
        .join(Save, (Save.target_id == Item.id) & (Save.target_type == "item"))\
        .where(Save.created_at >= start_30d)\
        .group_by(Item.category_id)
    for cid, cnt in db.session.execute(stmt):
        if cid in cat_map:
            cat_map[cid]["demand"] += cnt or 0

    stmt = select(Content.category_id, func.count(Content.id)).group_by(Content.category_id)
    for cid, cnt in db.session.execute(stmt):
        if cid in cat_map:
            cat_map[cid]["content_count"] = cnt or 0

    sorted_by_demand = sorted(cat_map.values(), key=lambda x: x["demand"], reverse=True)
    for rank, item in enumerate(sorted_by_demand, 1):
        item["demand_rank"] = rank

    sorted_by_volume = sorted(cat_map.values(), key=lambda x: x["content_count"], reverse=True)
    for rank, item in enumerate(sorted_by_volume, 1):
        item["volume_rank"] = rank

    cat_opps = []
    for item in cat_map.values():
        item["gap_score"] = item["volume_rank"] - item["demand_rank"]
        if item["demand"] > 0:
            cat_opps.append(item)

    cat_opps.sort(key=lambda x: x["gap_score"], reverse=True)

    brands = db.session.execute(select(Brand.id, Brand.name)).all()
    brand_map = {b.id: {"id": b.id, "name": b.name, "demand": 0, "content_count": 0} for b in brands}

    stmt = select(Item.brand_id, func.count(View.id))\
        .join(View, (View.target_id == Item.id) & (View.target_type == "item"))\
        .where(View.created_at >= start_30d)\
        .group_by(Item.brand_id)
    for bid, cnt in db.session.execute(stmt):
        if bid in brand_map:
            brand_map[bid]["demand"] += cnt or 0

    stmt = select(Item.brand_id, func.count(ItemClick.id))\
        .join(ItemVariant, ItemVariant.item_id == Item.id)\
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)\
        .join(ItemClick, ItemClick.item_store_link_id == ItemStoreLink.id)\
        .where(ItemClick.created_at >= start_30d)\
        .group_by(Item.brand_id)
    for bid, cnt in db.session.execute(stmt):
        if bid in brand_map:
            brand_map[bid]["demand"] += cnt or 0

    stmt = select(Item.brand_id, func.count(Save.id))\
        .join(Save, (Save.target_id == Item.id) & (Save.target_type == "item"))\
        .where(Save.created_at >= start_30d)\
        .group_by(Item.brand_id)
    for bid, cnt in db.session.execute(stmt):
        if bid in brand_map:
            brand_map[bid]["demand"] += cnt or 0

    stmt = select(content_brands.c.brand_id, func.count(View.id))\
        .join(View, (View.target_id == content_brands.c.content_id) & (View.target_type == "content"))\
        .where(View.created_at >= start_30d)\
        .group_by(content_brands.c.brand_id)
    for bid, cnt in db.session.execute(stmt):
        if bid in brand_map:
            brand_map[bid]["demand"] += cnt or 0

    stmt = select(content_brands.c.brand_id, func.count(content_brands.c.content_id)).group_by(content_brands.c.brand_id)
    for bid, cnt in db.session.execute(stmt):
        if bid in brand_map:
            brand_map[bid]["content_count"] = cnt or 0

    sorted_brands_demand = sorted(brand_map.values(), key=lambda x: x["demand"], reverse=True)
    for rank, item in enumerate(sorted_brands_demand, 1):
        item["demand_rank"] = rank

    sorted_brands_volume = sorted(brand_map.values(), key=lambda x: x["content_count"], reverse=True)
    for rank, item in enumerate(sorted_brands_volume, 1):
        item["volume_rank"] = rank

    brand_opps = []
    for item in brand_map.values():
        item["gap_score"] = item["volume_rank"] - item["demand_rank"]
        if item["demand"] > 0:
            brand_opps.append(item)

    brand_opps.sort(key=lambda x: x["gap_score"], reverse=True)

    final_opps = []
    for co in cat_opps[:4]:
        final_opps.append({
            "type": "category",
            "name": co["name"],
            "demand_score": co["demand"],
            "coverage": co["content_count"],
            "opportunity": f"Create more {co['name']} content."
        })
    for bo in brand_opps[:4]:
        final_opps.append({
            "type": "brand",
            "name": bo["name"],
            "demand_score": bo["demand"],
            "coverage": bo["content_count"],
            "opportunity": f"Create more {bo['name']} reviews."
        })

    return final_opps

def get_content_vs_product_performance():
    categories = db.session.execute(select(Category.id, Category.name, Category.slug)).all()
    cat_map = {
        c.id: {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "content_engagement": 0,
            "product_engagement": 0,
        }
        for c in categories
    }

    stmt = select(
        Content.category_id,
        func.sum(Content.view_count + Content.like_count + Content.dislike_count + Content.save_count + Content.comment_count)
    ).group_by(Content.category_id)
    for cid, val in db.session.execute(stmt):
        if cid in cat_map:
            cat_map[cid]["content_engagement"] = int(val or 0)

    stmt = select(
        Item.category_id,
        func.sum(Item.view_count + Item.click_count + Item.save_count)
    ).group_by(Item.category_id)
    for cid, val in db.session.execute(stmt):
        if cid in cat_map:
            cat_map[cid]["product_engagement"] = int(val or 0)

    items = list(cat_map.values())
    if not items:
        return []

    sorted_content = sorted(items, key=lambda x: x["content_engagement"], reverse=True)
    sorted_product = sorted(items, key=lambda x: x["product_engagement"], reverse=True)

    median_content = sorted_content[len(sorted_content) // 2]["content_engagement"] if sorted_content else 0
    median_product = sorted_product[len(sorted_product) // 2]["product_engagement"] if sorted_product else 0

    for item in items:
        hc = item["content_engagement"] >= median_content and item["content_engagement"] > 0
        hp = item["product_engagement"] >= median_product and item["product_engagement"] > 0

        if hc and not hp:
            item["status"] = "High Content, Low Product"
        elif hp and not hc:
            item["status"] = "High Product, Low Content"
        elif hc and hp:
            item["status"] = "High Both"
        else:
            item["status"] = "Low Both"

    return items

def get_intent_opportunity_data():
    categories = db.session.execute(select(Category.id, Category.name)).all()
    intents = db.session.execute(select(IntentFacet.id, IntentFacet.name, IntentFacet.slug)).all()
    intent_map = {i.id: i for i in intents}

    stmt = select(
        Content.category_id,
        Content.intent_id,
        func.count(Content.id).label("cnt")
    ).group_by(Content.category_id, Content.intent_id)

    rows = db.session.execute(stmt).all()

    cat_intents = {c.id: {i.slug: 0 for i in intents} for c in categories}
    for category_id, intent_id, cnt in rows:
        if category_id in cat_intents and intent_id in intent_map:
            slug = intent_map[intent_id].slug
            cat_intents[category_id][slug] = cnt

    expected_intents = ['buying-guide', 'review', 'comparison', 'tutorial', 'news', 'gift-ideas', 'top-list']

    results = []
    for c_id, c_name in categories:
        distribution = cat_intents.get(c_id, {})
        missing = [intent for intent in expected_intents if distribution.get(intent, 0) == 0]

        if missing:
            rec_intent = missing[0]
            opportunity = f"Increase {rec_intent.replace('-', ' ')} content"
        else:
            sorted_intents = sorted(expected_intents, key=lambda x: distribution.get(x, 0))
            rec_intent = sorted_intents[0]
            opportunity = f"Increase {rec_intent.replace('-', ' ')} content"

        formatted_distribution = {
            i.name: distribution.get(i.slug, 0) for i in intents
        }

        results.append({
            "category_name": c_name,
            "distribution": formatted_distribution,
            "opportunity": opportunity
        })

    return results

def get_content_coverage_matrix():
    categories = db.session.execute(select(Category.id, Category.name)).all()
    cat_map = {c.id: {
        "name": c.name,
        "demand_score": 0,
        "content_count": 0,
        "product_count": 0
    } for c in categories}

    stmt_content = select(
        Content.category_id,
        func.sum(Content.view_count + Content.like_count + Content.dislike_count + Content.save_count + Content.comment_count)
    ).group_by(Content.category_id)
    for cid, val in db.session.execute(stmt_content).all():
        if cid in cat_map:
            cat_map[cid]["demand_score"] += int(val or 0)

    stmt_item = select(
        Item.category_id,
        func.sum(Item.view_count + Item.click_count + Item.save_count)
    ).group_by(Item.category_id)
    for cid, val in db.session.execute(stmt_item).all():
        if cid in cat_map:
            cat_map[cid]["demand_score"] += int(val or 0)

    stmt_content_count = select(Content.category_id, func.count(Content.id)).group_by(Content.category_id)
    for cid, val in db.session.execute(stmt_content_count).all():
        if cid in cat_map:
            cat_map[cid]["content_count"] = val or 0

    stmt_prod_count = select(Item.category_id, func.count(Item.id)).group_by(Item.category_id)
    for cid, val in db.session.execute(stmt_prod_count).all():
        if cid in cat_map:
            cat_map[cid]["product_count"] = val or 0

    results = list(cat_map.values())
    if not results:
        return []

    results.sort(key=lambda x: x["demand_score"], reverse=True)
    num_cats = len(results)

    for rank, cat in enumerate(results):
        pct = rank / num_cats if num_cats > 0 else 0
        if pct <= 0.35:
            cat["demand"] = "High"
        elif pct <= 0.70:
            cat["demand"] = "Medium"
        else:
            cat["demand"] = "Low"

    results.sort(key=lambda x: x["content_count"], reverse=True)
    for rank, cat in enumerate(results):
        pct = rank / num_cats if num_cats > 0 else 0
        if pct <= 0.35:
            cat["coverage"] = "High"
        elif pct <= 0.70:
            cat["coverage"] = "Medium"
        else:
            cat["coverage"] = "Low"

    for cat in results:
        d = cat["demand"]
        c = cat["coverage"]
        if d == "High" and c == "Low":
            cat["gap_score"] = "High Gap"
        elif d == "High" and c == "Medium":
            cat["gap_score"] = "High Gap"
        elif d == "Medium" and c == "Low":
            cat["gap_score"] = "Medium Gap"
        elif d == "Low" and c == "High":
            cat["gap_score"] = "Low Gap"
        elif c == "High":
            cat["gap_score"] = "Low Gap"
        else:
            cat["gap_score"] = "Medium Gap"

    gap_priority = {"High Gap": 3, "Medium Gap": 2, "Low Gap": 1}
    results.sort(key=lambda x: (gap_priority.get(x["gap_score"], 0), x["demand_score"]), reverse=True)
    return results

def get_entity_momentum(name: str, entity_type: str) -> float:
    """
    Returns the percentage change in engagement over the last 7 days vs prior 7 days
    for a given Category or Brand name.
    """
    try:
        if entity_type.lower() == "category":
            trends = get_trending_categories_data()
        else:
            trends = get_trending_brands_data()
        for t in trends:
            if t["name"].lower() == name.lower():
                return float(t["pct_change"])
    except Exception:
        pass
    return 0.0

def get_content_decay(content_id: int) -> float:
    """
    Calculates the content decay rate (percentage traffic drop in views
    over the past 30 days compared to the preceding 30 days).
    Returns a decay factor (percentage drop, e.g. 25.0).
    """
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    start_a = now - timedelta(days=30)
    start_b = now - timedelta(days=60)
    
    try:
        views_a = db.session.execute(
            select(func.count(View.id))
            .where((View.target_id == content_id) & (View.target_type == "content") & (View.created_at >= start_a))
        ).scalar() or 0
        
        views_b = db.session.execute(
            select(func.count(View.id))
            .where((View.target_id == content_id) & (View.target_type == "content") & (View.created_at >= start_b) & (View.created_at < start_a))
        ).scalar() or 0
        
        if views_b > 0 and views_a < views_b:
            return round(((views_b - views_a) / views_b) * 100.0, 1)
    except Exception:
        pass
    return 0.0