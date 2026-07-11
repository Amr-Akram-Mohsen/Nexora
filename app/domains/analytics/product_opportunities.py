from sqlalchemy import func, select, desc, case, cast, Integer
from functools import lru_cache
from app.core.extensions import db
from app.domains.interaction.models import View, Reaction, Comment, Save, ProductClick, RecommendationImpression, RecommendationClick
from app.domains.content.models import Content
from app.domains.product.models import Product, ProductStoreLink, ProductVariant
from app.domains.taxonomy.models import Category, Brand, Entity, IntentFacet
from app.domains.relationships import ContentEntity
from app.domains.analytics.shared import (
    get_start_date,
    finalize_trend_stats,
    build_period_split_query,
    compute_quality_scores
)

def get_top_products_data(time_frame: str, limit: int = 5):
    start_date = get_start_date(time_frame)

    # 1. Most viewed products
    stmt_views = select(View.target_id, func.count(View.id).label("cnt")).where(View.target_type == "product")
    if start_date:
        stmt_views = stmt_views.where(View.created_at >= start_date)
    stmt_views = stmt_views.group_by(View.target_id).order_by(desc("cnt")).limit(limit)
    views_res = db.session.execute(stmt_views).all()

    # 2. Most clicked products
    stmt_clicks = (
        select(ProductVariant.product_id, func.count(ProductClick.id).label("cnt"))
        .join(ProductStoreLink, ProductStoreLink.variant_id == ProductVariant.id)
        .join(ProductClick, ProductClick.product_store_link_id == ProductStoreLink.id)
    )
    if start_date:
        stmt_clicks = stmt_clicks.where(ProductClick.created_at >= start_date)
    stmt_clicks = stmt_clicks.group_by(ProductVariant.product_id).order_by(desc("cnt")).limit(limit)
    clicks_res = db.session.execute(stmt_clicks).all()

    # 3. Most saved products
    stmt_saves = select(Save.target_id, func.count(Save.id).label("cnt")).where(Save.target_type == "product")
    if start_date:
        stmt_saves = stmt_saves.where(Save.created_at >= start_date)
    stmt_saves = stmt_saves.group_by(Save.target_id).order_by(desc("cnt")).limit(limit)
    saves_res = db.session.execute(stmt_saves).all()

    # Gather all unique product IDs
    all_product_ids = set()
    for row in views_res + clicks_res + saves_res:
        all_product_ids.add(row[0])

    item_map = {}
    if all_product_ids:
        products = db.session.execute(select(Product).where(Product.id.in_(all_product_ids))).scalars().all()
        item_map = {product.id: product for product in products}

    def format_list(results):
        formatted = []
        for iid, count in results:
            product = item_map.get(iid)
            if product:
                formatted.append({
                    "id": iid,
                    "name": product.name,
                    "count": count
                })
        return formatted

    return {
        "most_viewed": format_list(views_res),
        "most_clicked": format_list(clicks_res),
        "most_saved": format_list(saves_res),
    }

def get_brand_opportunity_data():
    brands = db.session.execute(
        select(Entity.id, Entity.name)
        .where((Entity.entity_type == "brand") | (Entity.entity_type == "organization"))
    ).all()
    brand_data = {b.id: {
        "name": b.name,
        "article_volume": 0,
        "product_volume": 0,
        "engagement": 0
    } for b in brands}

    art_vol_stmt = select(
        ContentEntity.entity_id,
        func.count(ContentEntity.content_id).label("count")
    ).group_by(ContentEntity.entity_id)
    for b_id, count in db.session.execute(art_vol_stmt).all():
        if b_id in brand_data:
            brand_data[b_id]["article_volume"] = count

    prod_vol_stmt = select(
        Entity.id,
        func.count(Product.id).label("count")
    ).join(Brand, Brand.slug == Entity.slug)\
     .join(Product, Product.brand_id == Brand.id)\
     .group_by(Entity.id)
    for b_id, count in db.session.execute(prod_vol_stmt).all():
        if b_id in brand_data:
            brand_data[b_id]["product_volume"] = count

    brand_content_eng_stmt = select(
        ContentEntity.entity_id,
        func.sum(
            Content.view_count + Content.like_count + Content.dislike_count + Content.save_count + Content.comment_count
        ).label("eng")
    ).join(Content, Content.id == ContentEntity.content_id)\
     .group_by(ContentEntity.entity_id)
    for b_id, eng in db.session.execute(brand_content_eng_stmt).all():
        if b_id in brand_data:
            brand_data[b_id]["engagement"] += int(eng or 0)

    brand_prod_eng_stmt = select(
        Entity.id,
        func.sum(Product.view_count + Product.click_count + Product.save_count).label("eng")
    ).join(Brand, Brand.slug == Entity.slug)\
     .join(Product, Product.brand_id == Brand.id)\
     .group_by(Entity.id)
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

def get_catalog_health_report():
    from datetime import datetime, timedelta, timezone
    from app.domains.relationships import content_products
    from app.domains.product.models import ProductImage
    
    now = datetime.now(timezone.utc)
    stale_date = now - timedelta(days=30)
    
    total_items = db.session.execute(select(func.count(Product.id))).scalar() or 0
    
    items_with_images_stmt = select(func.count(func.distinct(ProductImage.product_id)))
    items_with_images = db.session.execute(items_with_images_stmt).scalar() or 0
    items_without_images = total_items - items_with_images
    
    items_with_links_stmt = select(func.count(func.distinct(ProductVariant.product_id)))\
        .join(ProductStoreLink, ProductStoreLink.variant_id == ProductVariant.id)\
        .where(ProductStoreLink.is_active == True)
    items_with_links = db.session.execute(items_with_links_stmt).scalar() or 0
    items_without_links = total_items - items_with_links
    
    stale_links_stmt = select(func.count(func.distinct(ProductVariant.product_id)))\
        .join(ProductStoreLink, ProductStoreLink.variant_id == ProductVariant.id)\
        .where((ProductStoreLink.is_active == True) & ((ProductStoreLink.last_checked_at < stale_date) | (ProductStoreLink.last_checked_at == None)))
    items_with_stale_pricing = db.session.execute(stale_links_stmt).scalar() or 0
    
    items_with_content_stmt = select(func.count(func.distinct(content_products.c.product_id)))
    items_with_content = db.session.execute(items_with_content_stmt).scalar() or 0
    items_without_content = total_items - items_with_content
    
    completeness_score = 0
    if total_items > 0:
        c_images = (items_with_images / total_items) * 100
        c_links = (items_with_links / total_items) * 100
        c_pricing = ((items_with_links - items_with_stale_pricing) / items_with_links * 100) if items_with_links > 0 else 0
        completeness_score = (c_images + c_links + c_pricing) / 3
        
    return {
        "total_items": total_items,
        "completeness_score": round(completeness_score, 1),
        "metrics": {
            "without_images": items_without_images,
            "without_images_pct": round((items_without_images / total_items * 100), 1) if total_items else 0,
            "without_links": items_without_links,
            "without_links_pct": round((items_without_links / total_items * 100), 1) if total_items else 0,
            "stale_pricing": items_with_stale_pricing,
            "stale_pricing_pct": round((items_with_stale_pricing / total_items * 100), 1) if total_items else 0,
            "without_content": items_without_content,
            "without_content_pct": round((items_without_content / total_items * 100), 1) if total_items else 0,
        }
    }

def get_source_intelligence():
    from app.domains.interaction.models import ProductClick
    from app.domains.product.models import Store
    from datetime import datetime, timedelta, timezone
    import random
    
    now = datetime.now(timezone.utc)
    stale_date = now - timedelta(days=30)
    
    stores = db.session.execute(select(Store)).scalars().all()
    store_stats = []
    
    for store in stores:
        active_links = db.session.execute(
            select(func.count(ProductStoreLink.id))
            .where((ProductStoreLink.store_id == store.id) & (ProductStoreLink.is_active == True))
        ).scalar() or 0
        
        if active_links == 0:
            continue
            
        stale_links = db.session.execute(
            select(func.count(ProductStoreLink.id))
            .where((ProductStoreLink.store_id == store.id) & (ProductStoreLink.is_active == True) & ((ProductStoreLink.last_synced_at < stale_date) | (ProductStoreLink.last_synced_at == None)))
        ).scalar() or 0
        
        clicks = db.session.execute(
            select(func.count(ProductClick.id))
            .join(ProductStoreLink, ProductStoreLink.id == ProductClick.product_store_link_id)
            .where(ProductStoreLink.store_id == store.id)
        ).scalar() or 0
        
        random.seed(store.id)
        conversion_potential = random.uniform(1.2, 4.5)
        
        stale_pct = (stale_links / active_links) * 100 if active_links > 0 else 0
        
        health_score = 100 - (stale_pct * 0.5) + (min(clicks, 1000) / 100)
        health_score = min(max(health_score, 0), 100)
        
        store_stats.append({
            "store_id": store.id,
            "store_name": store.name,
            "active_links": active_links,
            "stale_links_pct": round(stale_pct, 1),
            "total_clicks": clicks,
            "conversion_potential": round(conversion_potential, 2),
            "health_score": round(health_score, 1),
            "is_simulated": True
        })
        
    store_stats.sort(key=lambda x: x["health_score"], reverse=True)
    return store_stats

def get_content_commerce_attribution():
    from app.domains.content.models import Content
    from app.domains.relationships import content_products
    from app.domains.product.models import Product
    
    stmt = select(
        Content.id,
        Content.title,
        Content.view_count.label('content_views'),
        func.sum(Product.click_count).label('total_item_clicks'),
        func.count(Product.id).label('linked_items_count')
    ).select_from(Content)\
     .join(content_products, content_products.c.content_id == Content.id)\
     .join(Product, Product.id == content_products.c.product_id)\
     .group_by(Content.id)\
     .having(func.sum(Product.click_count) > 0)\
     .order_by(desc(func.sum(Product.click_count)))\
     .limit(10)
     
    rows = db.session.execute(stmt).all()
    
    results = []
    for r in rows:
        c_views = r.content_views or 1
        i_clicks = r.total_item_clicks or 0
        conversion_rate = (i_clicks / c_views) * 100
        
        results.append({
            "content_id": r.id,
            "content_title": r.title,
            "content_views": c_views,
            "total_item_clicks": i_clicks,
            "linked_items_count": r.linked_items_count,
            "attribution_rate": round(conversion_rate, 2)
        })
        
    return results

def get_source_authority_validation():
    from app.domains.taxonomy.models import Source
    from app.domains.content.models import Content
    
    stmt = select(
        Source.id,
        Source.name,
        Source.authority_score,
        func.count(Content.id).label('content_count'),
        func.sum(Content.view_count + Content.like_count + Content.save_count).label('total_engagement')
    ).select_from(Source)\
     .outerjoin(Content, Content.source_id == Source.id)\
     .where(Source.is_active == True)\
     .group_by(Source.id, Source.name, Source.authority_score)\
     .having(func.count(Content.id) > 0)
     
    rows = db.session.execute(stmt).all()
    
    results = []
    for r in rows:
        content_count = r.content_count or 1
        total_engagement = r.total_engagement or 0
        avg_engagement = total_engagement / content_count
        
        auth_score = r.authority_score or 1
        validation_ratio = avg_engagement / auth_score
        
        if validation_ratio > 50:
            status = "Undervalued"
            status_class = "badge-success"
        elif validation_ratio < 5:
            status = "Overvalued"
            status_class = "badge-danger"
        else:
            status = "Balanced"
            status_class = "badge-blue"
            
        results.append({
            "source_id": r.id,
            "source_name": r.name,
            "authority_score": r.authority_score,
            "content_count": r.content_count,
            "avg_engagement": round(avg_engagement, 1),
            "validation_ratio": round(validation_ratio, 2),
            "status": status,
            "status_class": status_class
        })
        
    results.sort(key=lambda x: x["validation_ratio"], reverse=True)
    return results

def get_geographic_demand_data():
    from app.domains.interaction.models import ProductClick
    from app.domains.product.models import ProductStoreLink, Product
    from app.domains.taxonomy.models import Category
    
    stmt = select(
        Category.id.label("category_id"),
        Category.name.label("category_name"),
        ProductClick.country,
        func.count(ProductClick.id).label("click_count")
    ).select_from(ProductClick)\
     .join(ProductStoreLink, ProductClick.target_id == ProductStoreLink.id)\
     .join(Product, ProductStoreLink.product_id == Product.id)\
     .join(Category, Product.category_id == Category.id)\
     .where(ProductClick.country.isnot(None))\
     .where(ProductClick.country != "")\
     .group_by(Category.id, Category.name, ProductClick.country)
     
    rows = db.session.execute(stmt).all()
    
    cat_data = {}
    for r in rows:
        cid = r.category_id
        if cid not in cat_data:
            cat_data[cid] = {
                "category_name": r.category_name,
                "countries": []
            }
        cat_data[cid]["countries"].append({
            "country": r.country,
            "click_count": r.click_count
        })
        
    results = []
    for cid, data in cat_data.items():
        data["countries"].sort(key=lambda x: x["click_count"], reverse=True)
        data["countries"] = data["countries"][:5]
        data["total_clicks"] = sum(c["click_count"] for c in data["countries"])
        results.append(data)
        
    results.sort(key=lambda x: x["total_clicks"], reverse=True)
    return results

def get_recommendation_commerce_chain():
    from app.domains.interaction.models import RecommendationClick
    from app.domains.product.models import Product
    from app.domains.relationships import content_products
    from app.domains.content.models import Content
    
    cast_entity_id = cast(RecommendationClick.entity_id, Integer)
    
    stmt = select(
        Content.id,
        Content.title,
        func.count(RecommendationClick.id).label('rec_clicks')
    ).select_from(RecommendationClick)\
     .join(Product, (RecommendationClick.entity_type.in_(['shop_product', 'related_product'])) & (cast_entity_id == Product.id))\
     .join(content_products, Product.id == content_products.c.product_id)\
     .join(Content, content_products.c.content_id == Content.id)\
     .group_by(Content.id, Content.title)\
     .having(func.count(RecommendationClick.id) > 0)\
     .order_by(desc('rec_clicks'))\
     .limit(10)
     
    rows = db.session.execute(stmt).all()
    
    return [
        {
            "content_id": r.id,
            "title": r.title,
            "recommendation_clicks": r.rec_clicks
        }
        for r in rows
    ]
