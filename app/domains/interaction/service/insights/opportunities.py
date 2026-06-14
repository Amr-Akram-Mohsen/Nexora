# app/domains/interaction/service/insights/opportunities.py
from sqlalchemy import func, select, desc, case
from app.core.extensions import db
from app.domains.interaction.models import View, Reaction, Comment, Save, ItemClick, RecommendationImpression, RecommendationClick
from app.domains.content.models import Content
from app.domains.item.models import Item, ItemStoreLink, ItemVariant
from app.domains.taxonomy.models import Category, Brand, Topic, IntentFacet
from app.domains.relationships import content_brands, content_topics
from app.domains.interaction.service.insights.shared import get_start_date

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

def get_trending_categories_data():
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    start_a = now - timedelta(days=7)
    start_b = now - timedelta(days=14)

    categories = db.session.execute(select(Category.id, Category.name, Category.slug)).all()
    cat_stats = {
        c.id: {"id": c.id, "name": c.name, "slug": c.slug, "period_a": 0, "period_b": 0}
        for c in categories
    }

    def add_content_stats(stmt):
        for cid, a, b in db.session.execute(stmt):
            if cid in cat_stats:
                cat_stats[cid]["period_a"] += a or 0
                cat_stats[cid]["period_b"] += b or 0

    # 1. Content Views
    add_content_stats(
        select(
            Content.category_id,
            func.count(case((View.created_at >= start_a, View.id))).label("a"),
            func.count(case(((View.created_at >= start_b) & (View.created_at < start_a), View.id))).label("b")
        ).join(View, (View.target_id == Content.id) & (View.target_type == "content")).group_by(Content.category_id)
    )

    # 2. Content Reactions
    add_content_stats(
        select(
            Content.category_id,
            func.count(case((Reaction.created_at >= start_a, Reaction.id))).label("a"),
            func.count(case(((Reaction.created_at >= start_b) & (Reaction.created_at < start_a), Reaction.id))).label("b")
        ).join(Reaction, (Reaction.target_id == Content.id) & (Reaction.target_type == "content")).group_by(Content.category_id)
    )

    # 3. Content Comments
    add_content_stats(
        select(
            Content.category_id,
            func.count(case((Comment.created_at >= start_a, Comment.id))).label("a"),
            func.count(case(((Comment.created_at >= start_b) & (Comment.created_at < start_a), Comment.id))).label("b")
        ).join(Comment, (Comment.target_id == Content.id) & (Comment.target_type == "content")).group_by(Content.category_id)
    )

    # 4. Content Saves
    add_content_stats(
        select(
            Content.category_id,
            func.count(case((Save.created_at >= start_a, Save.id))).label("a"),
            func.count(case(((Save.created_at >= start_b) & (Save.created_at < start_a), Save.id))).label("b")
        ).join(Save, (Save.target_id == Content.id) & (Save.target_type == "content")).group_by(Content.category_id)
    )

    # 5. Item Views
    add_content_stats(
        select(
            Item.category_id,
            func.count(case((View.created_at >= start_a, View.id))).label("a"),
            func.count(case(((View.created_at >= start_b) & (View.created_at < start_a), View.id))).label("b")
        ).join(View, (View.target_id == Item.id) & (View.target_type == "item")).group_by(Item.category_id)
    )

    # 6. Item Reactions
    add_content_stats(
        select(
            Item.category_id,
            func.count(case((Reaction.created_at >= start_a, Reaction.id))).label("a"),
            func.count(case(((Reaction.created_at >= start_b) & (Reaction.created_at < start_a), Reaction.id))).label("b")
        ).join(Reaction, (Reaction.target_id == Item.id) & (Reaction.target_type == "item")).group_by(Item.category_id)
    )

    # 7. Item Comments
    add_content_stats(
        select(
            Item.category_id,
            func.count(case((Comment.created_at >= start_a, Comment.id))).label("a"),
            func.count(case(((Comment.created_at >= start_b) & (Comment.created_at < start_a), Comment.id))).label("b")
        ).join(Comment, (Comment.target_id == Item.id) & (Comment.target_type == "item")).group_by(Item.category_id)
    )

    # 8. Item Saves
    add_content_stats(
        select(
            Item.category_id,
            func.count(case((Save.created_at >= start_a, Save.id))).label("a"),
            func.count(case(((Save.created_at >= start_b) & (Save.created_at < start_a), Save.id))).label("b")
        ).join(Save, (Save.target_id == Item.id) & (Save.target_type == "item")).group_by(Item.category_id)
    )

    # 9. Item Clicks
    item_clicks_stmt = select(
        ItemVariant.item_id,
        func.count(case((ItemClick.created_at >= start_a, ItemClick.id))).label("a"),
        func.count(case(((ItemClick.created_at >= start_b) & (ItemClick.created_at < start_a), ItemClick.id))).label("b")
    ).join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)\
     .join(ItemClick, ItemClick.item_store_link_id == ItemStoreLink.id)\
     .group_by(ItemVariant.item_id)
    item_clicks = db.session.execute(item_clicks_stmt).all()

    if item_clicks:
        item_ids = [row[0] for row in item_clicks]
        items = db.session.execute(select(Item.id, Item.category_id).where(Item.id.in_(item_ids))).all()
        item_cat_map = {item_id: cat_id for item_id, cat_id in items}
        for item_id, a, b in item_clicks:
            cid = item_cat_map.get(item_id)
            if cid and cid in cat_stats:
                cat_stats[cid]["period_a"] += a or 0
                cat_stats[cid]["period_b"] += b or 0

    results = []
    for stat in cat_stats.values():
        a = stat["period_a"]
        b = stat["period_b"]
        change = a - b
        pct = ((a - b) / b * 100.0) if b > 0 else (100.0 if a > 0 else 0.0)
        results.append({
            "id": stat["id"],
            "name": stat["name"],
            "slug": stat["slug"],
            "period_a": a,
            "period_b": b,
            "change": change,
            "pct_change": round(pct, 1)
        })

    results.sort(key=lambda x: (x["period_a"], x["change"]), reverse=True)
    return results

def get_trending_brands_data():
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    start_a = now - timedelta(days=7)
    start_b = now - timedelta(days=14)

    brands = db.session.execute(select(Brand.id, Brand.name, Brand.slug)).all()
    brand_stats = {
        b.id: {"id": b.id, "name": b.name, "slug": b.slug, "period_a": 0, "period_b": 0}
        for b in brands
    }

    # Content Views for Brands
    stmt = select(
        content_brands.c.brand_id,
        func.count(case((View.created_at >= start_a, View.id))).label("a"),
        func.count(case(((View.created_at >= start_b) & (View.created_at < start_a), View.id))).label("b")
    ).join(View, (View.target_id == content_brands.c.content_id) & (View.target_type == "content")).group_by(content_brands.c.brand_id)
    for bid, a, b in db.session.execute(stmt):
        if bid in brand_stats:
            brand_stats[bid]["period_a"] += a or 0
            brand_stats[bid]["period_b"] += b or 0

    # Content Reactions
    stmt = select(
        content_brands.c.brand_id,
        func.count(case((Reaction.created_at >= start_a, Reaction.id))).label("a"),
        func.count(case(((Reaction.created_at >= start_b) & (Reaction.created_at < start_a), Reaction.id))).label("b")
    ).join(Reaction, (Reaction.target_id == content_brands.c.content_id) & (Reaction.target_type == "content")).group_by(content_brands.c.brand_id)
    for bid, a, b in db.session.execute(stmt):
        if bid in brand_stats:
            brand_stats[bid]["period_a"] += a or 0
            brand_stats[bid]["period_b"] += b or 0

    # Content Comments
    stmt = select(
        content_brands.c.brand_id,
        func.count(case((Comment.created_at >= start_a, Comment.id))).label("a"),
        func.count(case(((Comment.created_at >= start_b) & (Comment.created_at < start_a), Comment.id))).label("b")
    ).join(Comment, (Comment.target_id == content_brands.c.content_id) & (Comment.target_type == "content")).group_by(content_brands.c.brand_id)
    for bid, a, b in db.session.execute(stmt):
        if bid in brand_stats:
            brand_stats[bid]["period_a"] += a or 0
            brand_stats[bid]["period_b"] += b or 0

    # Content Saves
    stmt = select(
        content_brands.c.brand_id,
        func.count(case((Save.created_at >= start_a, Save.id))).label("a"),
        func.count(case(((Save.created_at >= start_b) & (Save.created_at < start_a), Save.id))).label("b")
    ).join(Save, (Save.target_id == content_brands.c.content_id) & (Save.target_type == "content")).group_by(content_brands.c.brand_id)
    for bid, a, b in db.session.execute(stmt):
        if bid in brand_stats:
            brand_stats[bid]["period_a"] += a or 0
            brand_stats[bid]["period_b"] += b or 0

    # Item Views
    stmt = select(
        Item.brand_id,
        func.count(case((View.created_at >= start_a, View.id))).label("a"),
        func.count(case(((View.created_at >= start_b) & (View.created_at < start_a), View.id))).label("b")
    ).join(View, (View.target_id == Item.id) & (View.target_type == "item")).group_by(Item.brand_id)
    for bid, a, b in db.session.execute(stmt):
        if bid in brand_stats:
            brand_stats[bid]["period_a"] += a or 0
            brand_stats[bid]["period_b"] += b or 0

    # Item Reactions
    stmt = select(
        Item.brand_id,
        func.count(case((Reaction.created_at >= start_a, Reaction.id))).label("a"),
        func.count(case(((Reaction.created_at >= start_b) & (Reaction.created_at < start_a), Reaction.id))).label("b")
    ).join(Reaction, (Reaction.target_id == Item.id) & (Reaction.target_type == "item")).group_by(Item.brand_id)
    for bid, a, b in db.session.execute(stmt):
        if bid in brand_stats:
            brand_stats[bid]["period_a"] += a or 0
            brand_stats[bid]["period_b"] += b or 0

    # Item Comments
    stmt = select(
        Item.brand_id,
        func.count(case((Comment.created_at >= start_a, Comment.id))).label("a"),
        func.count(case(((Comment.created_at >= start_b) & (Comment.created_at < start_a), Comment.id))).label("b")
    ).join(Comment, (Comment.target_id == Item.id) & (Comment.target_type == "item")).group_by(Item.brand_id)
    for bid, a, b in db.session.execute(stmt):
        if bid in brand_stats:
            brand_stats[bid]["period_a"] += a or 0
            brand_stats[bid]["period_b"] += b or 0

    # Item Saves
    stmt = select(
        Item.brand_id,
        func.count(case((Save.created_at >= start_a, Save.id))).label("a"),
        func.count(case(((Save.created_at >= start_b) & (Save.created_at < start_a), Save.id))).label("b")
    ).join(Save, (Save.target_id == Item.id) & (Save.target_type == "item")).group_by(Item.brand_id)
    for bid, a, b in db.session.execute(stmt):
        if bid in brand_stats:
            brand_stats[bid]["period_a"] += a or 0
            brand_stats[bid]["period_b"] += b or 0

    # Item Clicks
    stmt = select(
        ItemVariant.item_id,
        func.count(case((ItemClick.created_at >= start_a, ItemClick.id))).label("a"),
        func.count(case(((ItemClick.created_at >= start_b) & (ItemClick.created_at < start_a), ItemClick.id))).label("b")
    ).join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)\
     .join(ItemClick, ItemClick.item_store_link_id == ItemStoreLink.id)\
     .group_by(ItemVariant.item_id)
    item_clicks = db.session.execute(stmt).all()
    if item_clicks:
        item_ids = [row[0] for row in item_clicks]
        items = db.session.execute(select(Item.id, Item.brand_id).where(Item.id.in_(item_ids))).all()
        item_brand_map = {item_id: brand_id for item_id, brand_id in items}
        for item_id, a, b in item_clicks:
            bid = item_brand_map.get(item_id)
            if bid and bid in brand_stats:
                brand_stats[bid]["period_a"] += a or 0
                brand_stats[bid]["period_b"] += b or 0

    results = []
    for stat in brand_stats.values():
        a = stat["period_a"]
        b = stat["period_b"]
        change = a - b
        pct = ((a - b) / b * 100.0) if b > 0 else (100.0 if a > 0 else 0.0)
        results.append({
            "id": stat["id"],
            "name": stat["name"],
            "slug": stat["slug"],
            "period_a": a,
            "period_b": b,
            "change": change,
            "pct_change": round(pct, 1)
        })

    results.sort(key=lambda x: (x["period_a"], x["change"]), reverse=True)
    return results

def get_trending_topics_data():
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    start_a = now - timedelta(days=7)
    start_b = now - timedelta(days=14)

    topics = db.session.execute(select(Topic.id, Topic.name, Topic.slug)).all()
    topic_stats = {
        t.id: {"id": t.id, "name": t.name, "slug": t.slug, "period_a": 0, "period_b": 0}
        for t in topics
    }

    # Content Views
    stmt = select(
        content_topics.c.topic_id,
        func.count(case((View.created_at >= start_a, View.id))).label("a"),
        func.count(case(((View.created_at >= start_b) & (View.created_at < start_a), View.id))).label("b")
    ).join(View, (View.target_id == content_topics.c.content_id) & (View.target_type == "content")).group_by(content_topics.c.topic_id)
    for tid, a, b in db.session.execute(stmt):
        if tid in topic_stats:
            topic_stats[tid]["period_a"] += a or 0
            topic_stats[tid]["period_b"] += b or 0

    # Content Reactions
    stmt = select(
        content_topics.c.topic_id,
        func.count(case((Reaction.created_at >= start_a, Reaction.id))).label("a"),
        func.count(case(((Reaction.created_at >= start_b) & (Reaction.created_at < start_a), Reaction.id))).label("b")
    ).join(Reaction, (Reaction.target_id == content_topics.c.content_id) & (Reaction.target_type == "content")).group_by(content_topics.c.topic_id)
    for tid, a, b in db.session.execute(stmt):
        if tid in topic_stats:
            topic_stats[tid]["period_a"] += a or 0
            topic_stats[tid]["period_b"] += b or 0

    # Content Comments
    stmt = select(
        content_topics.c.topic_id,
        func.count(case((Comment.created_at >= start_a, Comment.id))).label("a"),
        func.count(case(((Comment.created_at >= start_b) & (Comment.created_at < start_a), Comment.id))).label("b")
    ).join(Comment, (Comment.target_id == content_topics.c.content_id) & (Comment.target_type == "content")).group_by(content_topics.c.topic_id)
    for tid, a, b in db.session.execute(stmt):
        if tid in topic_stats:
            topic_stats[tid]["period_a"] += a or 0
            topic_stats[tid]["period_b"] += b or 0

    # Content Saves
    stmt = select(
        content_topics.c.topic_id,
        func.count(case((Save.created_at >= start_a, Save.id))).label("a"),
        func.count(case(((Save.created_at >= start_b) & (Save.created_at < start_a), Save.id))).label("b")
    ).join(Save, (Save.target_id == content_topics.c.content_id) & (Save.target_type == "content")).group_by(content_topics.c.topic_id)
    for tid, a, b in db.session.execute(stmt):
        if tid in topic_stats:
            topic_stats[tid]["period_a"] += a or 0
            topic_stats[tid]["period_b"] += b or 0

    results = []
    for stat in topic_stats.values():
        a = stat["period_a"]
        b = stat["period_b"]
        change = a - b
        pct = ((a - b) / b * 100.0) if b > 0 else (100.0 if a > 0 else 0.0)
        results.append({
            "id": stat["id"],
            "name": stat["name"],
            "slug": stat["slug"],
            "period_a": a,
            "period_b": b,
            "change": change,
            "pct_change": round(pct, 1)
        })

    results.sort(key=lambda x: (x["period_a"], x["change"]), reverse=True)
    return results

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
            item["status_class"] = "badge-info"
        elif hp and not hc:
            item["status"] = "High Product, Low Content"
            item["status_class"] = "badge-warning"
        elif hc and hp:
            item["status"] = "High Both"
            item["status_class"] = "badge-success"
        else:
            item["status"] = "Low Both"
            item["status_class"] = "badge-secondary"

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

def get_recommendation_performance_data():
    related_content_impressions = db.session.execute(
        select(func.count(RecommendationImpression.id)).where(RecommendationImpression.entity_type == 'related_content')
    ).scalar() or 0
    related_products_impressions = db.session.execute(
        select(func.count(RecommendationImpression.id)).where(RecommendationImpression.entity_type == 'related_product')
    ).scalar() or 0
    shop_products_impressions = db.session.execute(
        select(func.count(RecommendationImpression.id)).where(RecommendationImpression.entity_type == 'shop_product')
    ).scalar() or 0

    related_content_clicks = db.session.execute(
        select(func.count(RecommendationClick.id)).where(RecommendationClick.entity_type == 'related_content')
    ).scalar() or 0
    related_products_clicks = db.session.execute(
        select(func.count(RecommendationClick.id)).where(RecommendationClick.entity_type == 'related_product')
    ).scalar() or 0
    shop_products_clicks = db.session.execute(
        select(func.count(RecommendationClick.id)).where(RecommendationClick.entity_type == 'shop_product')
    ).scalar() or 0

    related_content_ctr = round((related_content_clicks / related_content_impressions) * 100.0, 2) if related_content_impressions > 0 else 0.0
    related_products_ctr = round((related_products_clicks / related_products_impressions) * 100.0, 2) if related_products_impressions > 0 else 0.0
    shop_products_ctr = round((shop_products_clicks / shop_products_impressions) * 100.0, 2) if shop_products_impressions > 0 else 0.0

    total_impressions = related_content_impressions + related_products_impressions + shop_products_impressions
    total_clicks = related_content_clicks + related_products_clicks + shop_products_clicks
    overall_ctr = round((total_clicks / total_impressions) * 100.0, 2) if total_impressions > 0 else 0.0

    categories = db.session.execute(select(Category.id, Category.name)).all()
    cat_id_to_name = {cat.id: cat.name for cat in categories}
    
    content_cats = {row[0]: row[1] for row in db.session.execute(select(Content.id, Content.category_id)).all()}
    item_cats = {row[0]: row[1] for row in db.session.execute(select(Item.id, Item.category_id)).all()}

    def resolve_category_id(context_id_str, entity_type):
        if not context_id_str:
            return None
        try:
            c_id = int(context_id_str)
        except ValueError:
            return None
        if entity_type == 'shop_product':
            return content_cats.get(c_id)
        elif entity_type == 'related_product':
            return item_cats.get(c_id)
        elif entity_type == 'related_content':
            if c_id in content_cats:
                return content_cats[c_id]
            return item_cats.get(c_id)
        return None

    def resolve_page_type(context_id_str, entity_type):
        if not context_id_str:
            return None
        try:
            c_id = int(context_id_str)
        except ValueError:
            return None
        if entity_type == 'shop_product':
            return 'content'
        elif entity_type == 'related_product':
            return 'commercial'
        elif entity_type == 'related_content':
            if c_id in content_cats:
                return 'content'
            return 'commercial'
        return None

    all_impressions = db.session.execute(
        select(RecommendationImpression.context_id, RecommendationImpression.entity_type)
    ).all()
    all_clicks = db.session.execute(
        select(RecommendationClick.context_id, RecommendationClick.entity_type)
    ).all()

    cat_stats = {cat_id: {"impressions": 0, "clicks": 0} for cat_id in cat_id_to_name.keys()}
    for context_id_str, rectype in all_impressions:
        cat_id = resolve_category_id(context_id_str, rectype)
        if cat_id in cat_stats:
            cat_stats[cat_id]["impressions"] += 1
            
    for context_id_str, rectype in all_clicks:
        cat_id = resolve_category_id(context_id_str, rectype)
        if cat_id in cat_stats:
            cat_stats[cat_id]["clicks"] += 1

    category_metrics = []
    for cat_id, name in cat_id_to_name.items():
        stats = cat_stats[cat_id]
        ctr = (stats["clicks"] / stats["impressions"] * 100.0) if stats["impressions"] > 0 else 0.0
        category_metrics.append({
            "category_id": cat_id,
            "name": name,
            "impressions": stats["impressions"],
            "clicks": stats["clicks"],
            "ctr": round(ctr, 2)
        })

    page_stats = {
        "content": {"impressions": 0, "clicks": 0},
        "commercial": {"impressions": 0, "clicks": 0}
    }
    for context_id_str, rectype in all_impressions:
        ptype = resolve_page_type(context_id_str, rectype)
        if ptype in page_stats:
            page_stats[ptype]["impressions"] += 1

    for context_id_str, rectype in all_clicks:
        ptype = resolve_page_type(context_id_str, rectype)
        if ptype in page_stats:
            page_stats[ptype]["clicks"] += 1

    page_type_metrics = []
    for ptype in ["content", "commercial"]:
        stats = page_stats[ptype]
        ctr = (stats["clicks"] / stats["impressions"] * 100.0) if stats["impressions"] > 0 else 0.0
        page_type_metrics.append({
            "page_type": ptype,
            "impressions": stats["impressions"],
            "clicks": stats["clicks"],
            "ctr": round(ctr, 2)
        })

    rectype_stats = {
        "related_content": {"impressions": related_content_impressions, "clicks": related_content_clicks},
        "related_product": {"impressions": related_products_impressions, "clicks": related_products_clicks},
        "shop_product": {"impressions": shop_products_impressions, "clicks": shop_products_clicks}
    }
    recommendation_type_metrics = []
    for rtype, stats in rectype_stats.items():
        ctr = (stats["clicks"] / stats["impressions"] * 100.0) if stats["impressions"] > 0 else 0.0
        recommendation_type_metrics.append({
            "recommendation_type": rtype,
            "impressions": stats["impressions"],
            "clicks": stats["clicks"],
            "ctr": round(ctr, 2)
        })

    max_cat_ctr = max([c["ctr"] for c in category_metrics]) if category_metrics else 0.0
    max_cat_impressions = max([c["impressions"] for c in category_metrics]) if category_metrics else 0
    category_scores = {}
    for c in category_metrics:
        ctr = c["ctr"]
        impressions = c["impressions"]
        norm_ctr = (ctr / max_cat_ctr) if max_cat_ctr > 0 else 0.0
        engagement_weight = (impressions / max_cat_impressions) if max_cat_impressions > 0 else 0.0
        category_scores[c["name"]] = {
            "ctr": ctr,
            "impressions": impressions,
            "clicks": c["clicks"],
            "quality_score": round(norm_ctr * engagement_weight, 2)
        }

    max_page_ctr = max([p["ctr"] for p in page_type_metrics]) if page_type_metrics else 0.0
    max_page_impressions = max([p["impressions"] for p in page_type_metrics]) if page_type_metrics else 0
    page_type_scores = {}
    for p in page_type_metrics:
        ctr = p["ctr"]
        impressions = p["impressions"]
        norm_ctr = (ctr / max_page_ctr) if max_page_ctr > 0 else 0.0
        engagement_weight = (impressions / max_page_impressions) if max_page_impressions > 0 else 0.0
        page_type_scores[p["page_type"]] = {
            "ctr": ctr,
            "impressions": impressions,
            "clicks": p["clicks"],
            "quality_score": round(norm_ctr * engagement_weight, 2)
        }

    max_rec_ctr = max([r["ctr"] for r in recommendation_type_metrics]) if recommendation_type_metrics else 0.0
    max_rec_impressions = max([r["impressions"] for r in recommendation_type_metrics]) if recommendation_type_metrics else 0
    recommendation_type_scores = {}
    for r in recommendation_type_metrics:
        ctr = r["ctr"]
        impressions = r["impressions"]
        norm_ctr = (ctr / max_rec_ctr) if max_rec_ctr > 0 else 0.0
        engagement_weight = (impressions / max_rec_impressions) if max_rec_impressions > 0 else 0.0
        recommendation_type_scores[r["recommendation_type"]] = {
            "ctr": ctr,
            "impressions": impressions,
            "clicks": r["clicks"],
            "quality_score": round(norm_ctr * engagement_weight, 2)
        }

    diagnoses = {}
    for rtype in ["related_content", "related_product", "shop_product"]:
        stats = rectype_stats[rtype]
        ctr = (stats["clicks"] / stats["impressions"] * 100.0) if stats["impressions"] > 0 else 0.0
        
        if ctr < 5.0:
            classification = "Low"
        elif ctr <= 15.0:
            classification = "Medium"
        else:
            classification = "High"
            
        q_score = recommendation_type_scores[rtype]["quality_score"]
        
        if rtype == "related_content":
            if classification == "Low":
                issue = "Low user interest in recommended articles"
                diagnosis = "Generic related article suggestions are failing to engage users."
                recommended_action = "Replace with comparison-focused articles or buying guides in the sidebar."
                expected_impact = "Boost reader click-through rate and session depth by matching user search intent."
                confidence = 0.80
            elif classification == "Medium":
                issue = "Moderate engagement on related articles"
                diagnosis = "Articles are relevant but could benefit from clearer call-to-actions."
                recommended_action = "Optimize sidebar article headlines and add clear teaser cards."
                expected_impact = "Improve content engagement and time-on-site metrics."
                confidence = 0.75
            else:
                issue = "High content recommendation affinity"
                diagnosis = "Users are highly receptive to related reading materials."
                recommended_action = "Expand related content slots and pin top-performing articles."
                expected_impact = "Further increase internal page-views and brand trust."
                confidence = 0.90
        elif rtype == "related_product":
            if classification == "Low":
                issue = "Low product suggestion clicks on product pages"
                diagnosis = "Recommended products do not align well with the main item."
                recommended_action = "Refine product-to-product similarity weights to favor same-category items."
                expected_impact = "Recover lost commercial intent on product detail pages."
                confidence = 0.85
            elif classification == "Medium":
                issue = "Moderate related product conversions"
                diagnosis = "Recommendations are functional but lack visual/promotional appeal."
                recommended_action = "Introduce promotional badges (e.g., 'Best Value', 'Trending') on cards."
                expected_impact = "Increase cross-sell volume and merchant referrals."
                confidence = 0.80
            else:
                issue = "High product cross-sell performance"
                diagnosis = "Alternative/complementary product selections are highly effective."
                recommended_action = "Increase product card density in content pages and sidebar grids."
                expected_impact = "Maximize revenue from high-performing commercial links."
                confidence = 0.95
        else: # shop_product
            if classification == "Low":
                issue = "Low commercial conversion of article reader base"
                diagnosis = "Article readers are ignoring the 'Shop Related Products' box."
                recommended_action = "Align shop recommendations strictly with items directly mentioned in content body."
                expected_impact = "Increase monetization efficiency of informational traffic."
                confidence = 0.75
            elif classification == "Medium":
                issue = "Moderate shop card click-through rate"
                diagnosis = "Offers are seen but price/merchant options could be more competitive."
                recommended_action = "Prioritize merchants with lowest prices and best ratings in the shop block."
                expected_impact = "Improve click-out rate to external affiliate stores."
                confidence = 0.85
            else:
                issue = "Exceptional article-to-shop transition rate"
                diagnosis = "Shop widgets are capturing user buying intent perfectly."
                recommended_action = "Prominently display the shop widget above the fold in high-traffic reviews."
                expected_impact = "Substantially scale affiliate click out and revenue."
                confidence = 0.90
                
        diagnoses[rtype] = {
            "ctr": round(ctr, 2),
            "impressions": stats["impressions"],
            "clicks": stats["clicks"],
            "classification": classification,
            "quality_score": q_score,
            "action_suggestion": {
                "issue": issue,
                "diagnosis": diagnosis,
                "recommended_action": recommended_action,
                "expected_impact": expected_impact,
                "confidence": confidence
            }
        }

    active_categories = [c for c in category_metrics if c["impressions"] > 0]
    if active_categories:
        avg_baseline = sum([c["ctr"] for c in active_categories]) / len(active_categories)
    else:
        avg_baseline = 0.0

    category_deviations = {}
    for c in category_metrics:
        if c["impressions"] > 0:
            category_deviations[c["name"]] = round(c["ctr"] - avg_baseline, 2)
        else:
            category_deviations[c["name"]] = 0.0

    if active_categories:
        best_cat = max(active_categories, key=lambda x: x["ctr"])
        worst_cat = min(active_categories, key=lambda x: x["ctr"])
        best_performing = {
            "name": best_cat["name"],
            "ctr": best_cat["ctr"],
            "deviation": category_deviations[best_cat["name"]]
        }
        worst_performing = {
            "name": worst_cat["name"],
            "ctr": worst_cat["ctr"],
            "deviation": category_deviations[worst_cat["name"]]
        }
    else:
        best_performing = {"name": "N/A", "ctr": 0.0, "deviation": 0.0}
        worst_performing = {"name": "N/A", "ctr": 0.0, "deviation": 0.0}

    benchmarking = {
        "best_category": best_performing,
        "worst_category": worst_performing,
        "average_baseline": round(avg_baseline, 2),
        "category_deviations": category_deviations
    }

    return {
        "overall_ctr": overall_ctr,
        "related_products_ctr": related_products_ctr,
        "related_content_ctr": related_content_ctr,
        "shop_products_ctr": shop_products_ctr,
        "impressions": {
            "related_content": related_content_impressions,
            "related_product": related_products_impressions,
            "shop_product": shop_products_impressions,
            "total": total_impressions
        },
        "clicks": {
            "related_content": related_content_clicks,
            "related_product": related_products_clicks,
            "shop_product": shop_products_clicks,
            "total": total_clicks
        },
        "diagnoses": diagnoses,
        "quality_scores": {
            "categories": category_scores,
            "page_types": page_type_scores,
            "recommendation_types": recommendation_type_scores
        },
        "benchmarking": benchmarking
    }

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
            cat["gap_class"] = "badge-danger"
        elif d == "High" and c == "Medium":
            cat["gap_score"] = "High Gap"
            cat["gap_class"] = "badge-danger"
        elif d == "Medium" and c == "Low":
            cat["gap_score"] = "Medium Gap"
            cat["gap_class"] = "badge-warning"
        elif d == "Low" and c == "High":
            cat["gap_score"] = "Low Gap"
            cat["gap_class"] = "badge-success"
        elif c == "High":
            cat["gap_score"] = "Low Gap"
            cat["gap_class"] = "badge-success"
        else:
            cat["gap_score"] = "Medium Gap"
            cat["gap_class"] = "badge-warning"

    gap_priority = {"High Gap": 3, "Medium Gap": 2, "Low Gap": 1}
    results.sort(key=lambda x: (gap_priority.get(x["gap_score"], 0), x["demand_score"]), reverse=True)
    return results
