from sqlalchemy import select, func
from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.product.models import Product
from app.domains.relationships import content_products
from app.domains.interaction.models import RecommendationImpression, RecommendationClick
from datetime import datetime, timedelta, timezone

def get_recommendation_stats():
    total_matches = db.session.execute(
        select(func.count()).select_from(content_products)
    ).scalar() or 0

    linked_contents = db.session.execute(
        select(func.count(func.distinct(content_products.c.content_id)))
    ).scalar() or 0

    linked_items = db.session.execute(
        select(func.count(func.distinct(content_products.c.product_id)))
    ).scalar() or 0

    total_impressions = db.session.execute(
        select(func.count()).select_from(RecommendationImpression)
    ).scalar() or 0
    
    total_clicks = db.session.execute(
        select(func.count()).select_from(RecommendationClick)
    ).scalar() or 0
    
    overall_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
    
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    impressions_30d = db.session.execute(
        select(func.count()).select_from(RecommendationImpression)
        .where(RecommendationImpression.created_at >= thirty_days_ago)
    ).scalar() or 0
    
    clicks_30d = db.session.execute(
        select(func.count()).select_from(RecommendationClick)
        .where(RecommendationClick.created_at >= thirty_days_ago)
    ).scalar() or 0

    return {
        "total_matches":   total_matches,
        "linked_contents": linked_contents,
        "linked_items":    linked_items,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "overall_ctr": round(overall_ctr, 2),
        "impressions_30d": impressions_30d,
        "clicks_30d": clicks_30d,
    }

def fetch_admin_matches_page(page, per_page, search, entity_type=None, ctr_range=None):
    base_stmt = (
        select(Content.id)
        .join(content_products, Content.id == content_products.c.content_id)
    )
    if search:
        like = f"%{search}%"
        base_stmt = base_stmt.join(Product, Product.id == content_products.c.product_id)
        base_stmt = base_stmt.where(Content.title.ilike(like) | Product.name.ilike(like))
        
    context_id_expr = Content.object_type + '/' + func.cast(Content.object_id, db.String)

    if entity_type:
        base_stmt = base_stmt.where(
            select(RecommendationImpression.id)
            .where(RecommendationImpression.context_id == context_id_expr)
            .where(RecommendationImpression.entity_type == entity_type)
            .exists()
        )

    if ctr_range:
        imp_count = select(func.count(RecommendationImpression.id)).where(RecommendationImpression.context_id == context_id_expr).scalar_subquery()
        click_count = select(func.count(RecommendationClick.id)).where(RecommendationClick.context_id == context_id_expr).scalar_subquery()
        
        ctr_expr = (click_count * 100.0) / func.nullif(imp_count, 0)
        
        if ctr_range == 'high':
            base_stmt = base_stmt.where(ctr_expr > 3.0)
        elif ctr_range == 'medium':
            base_stmt = base_stmt.where(ctr_expr.between(1.0, 3.0))
        elif ctr_range == 'low':
            base_stmt = base_stmt.where(ctr_expr > 0.0).where(ctr_expr < 1.0)
        elif ctr_range == 'zero':
            base_stmt = base_stmt.where(func.coalesce(ctr_expr, 0) == 0).where(imp_count > 0)
    
    base_stmt = base_stmt.group_by(Content.id).order_by(func.max(Content.view_count).desc())

    from app.shared.utils.admin_helpers import execute_paginated_query
    
    total_stmt = select(func.count()).select_from(base_stmt.subquery())
    products, total, pages = execute_paginated_query(base_stmt, total_stmt, page, per_page)
    content_ids = [i[0] for i in products]

    if not content_ids:
        return total, pages, []

    detail_stmt = (
        select(Content, Product)
        .select_from(Content)
        .join(content_products, Content.id == content_products.c.content_id)
        .join(Product, Product.id == content_products.c.product_id)
        .where(Content.id.in_(content_ids))
    )
    rows = db.session.execute(detail_stmt).all()

    grouped = {}
    for content, product in rows:
        if content.id not in grouped:
            grouped[content.id] = {
                "content_id": content.id,
                "content_title": content.title or f"Content #{content.id}",
                "content_views": content.view_count or 0,
                "object_type": content.object_type,
                "object_id": content.object_id,
                "products": []
            }
        grouped[content.id]["products"].append(product)
    
    serialized = []
    for cid in content_ids:
        if cid in grouped:
            g = grouped[cid]
            context_id_val = f"{g['object_type']}/{g['object_id']}"
            
            widget_impressions = db.session.scalar(
                select(func.count(RecommendationImpression.id))
                .where(RecommendationImpression.context_id == context_id_val)
            ) or 0
            
            widget_clicks = db.session.scalar(
                select(func.count(RecommendationClick.id))
                .where(RecommendationClick.context_id == context_id_val)
            ) or 0
            
            widget_ctr = round((widget_clicks / widget_impressions * 100), 1) if widget_impressions > 0 else 0.0
            
            last_impression = db.session.scalar(
                select(func.max(RecommendationImpression.created_at))
                .where(RecommendationImpression.context_id == context_id_val)
            )
            
            last_active = "Never"
            if last_impression:
                if isinstance(last_impression, str):
                    last_active = last_impression[:16]
                else:
                    last_active = last_impression.strftime("%Y-%m-%d %H:%M")

            serialized.append({
                "content_id": g["content_id"],
                "content_title": g["content_title"],
                "content_views": g["content_views"],
                "widget_impressions": widget_impressions,
                "widget_clicks": widget_clicks,
                "widget_ctr": widget_ctr,
                "last_active": last_active,
                "linked_items_count": len(g["products"]),
                "products": [
                    {
                        "id": i.id,
                        "name": i.name or f"Product #{i.id}",
                        "type": i.product_type,
                        "clicks": i.click_count or 0
                    } for i in g["products"]
                ]
            })
    return total, pages, serialized

def get_admin_match_inspect_raw(content_id):
    from sqlalchemy.orm import selectinload
    content = db.session.execute(
        select(Content).options(selectinload(Content.linked_products)).where(Content.id == content_id)
    ).scalar_one_or_none()
    if not content:
        return None
        
    from app.domains.interaction.models import ProductClick
    from app.domains.product.models import ProductStoreLink, ProductVariant
    
    referrer_pattern = f"%{content.object_type}/{content.object_id}%" if content.object_id else f"%/{content.id}%"
    context_id_val = f"{content.object_type}/{content.object_id}" if content.object_id else f"article/{content.id}"
    
    widget_impressions = db.session.scalar(
        select(func.count(RecommendationImpression.id))
        .where(RecommendationImpression.context_id == context_id_val)
    ) or 0
    
    unique_users = db.session.scalar(
        select(func.count(func.distinct(RecommendationImpression.user_id)))
        .where(RecommendationImpression.context_id == context_id_val)
        .where(RecommendationImpression.user_id.isnot(None))
    ) or 0
    
    last_impression = db.session.scalar(
        select(func.max(RecommendationImpression.created_at))
        .where(RecommendationImpression.context_id == context_id_val)
    )
    
    linked_items_stats = []
    for i in content.linked_products:
        context_clicks = db.session.scalar(
            select(func.count(ProductClick.id))
            .join(ProductStoreLink, ProductClick.product_store_link_id == ProductStoreLink.id)
            .join(ProductVariant, ProductStoreLink.variant_id == ProductVariant.id)
            .where(ProductVariant.product_id == i.id)
            .where(ProductClick.referrer.ilike(referrer_pattern))
        ) or 0
        
        widget_clicks = db.session.scalar(
            select(func.count(RecommendationClick.id))
            .where(RecommendationClick.context_id == context_id_val)
            .where(RecommendationClick.entity_id == str(i.id))
        ) or 0
        
        linked_items_stats.append((i, context_clicks, widget_clicks))
        
    return (content, widget_impressions, unique_users, last_impression, linked_items_stats)

def get_admin_context_performance():
    stmt = (
        select(
            RecommendationImpression.context_id,
            RecommendationImpression.entity_type,
            func.count(RecommendationImpression.id).label("impressions"),
            func.coalesce(
                select(func.count(RecommendationClick.id))
                .where(RecommendationClick.context_id == RecommendationImpression.context_id)
                .scalar_subquery(), 0
            ).label("clicks")
        )
        .group_by(RecommendationImpression.context_id, RecommendationImpression.entity_type)
        .order_by(func.count(RecommendationImpression.id).desc())
        .limit(10)
    )
    
    rows = db.session.execute(stmt).all()
    results = []
    for r in rows:
        ctr = (r.clicks / r.impressions * 100) if r.impressions > 0 else 0
        results.append({
            "context_id": r.context_id,
            "entity_type": r.entity_type,
            "impressions": "{:,}".format(r.impressions),
            "clicks": "{:,}".format(r.clicks),
            "ctr": f"{ctr:.2f}%",
        })
    return results

def get_admin_entity_performance():
    stmt = (
        select(
            RecommendationClick.entity_id,
            RecommendationClick.entity_type,
            func.count(RecommendationClick.id).label("clicks")
        )
        .group_by(RecommendationClick.entity_id, RecommendationClick.entity_type)
        .order_by(func.count(RecommendationClick.id).desc())
        .limit(10)
    )
    
    rows = db.session.execute(stmt).all()
    results = []
    for r in rows:
        name = f"Entity #{r.entity_id}"
        if str(r.entity_id).isdigit():
            if r.entity_type == "related_content":
                content = db.session.get(Content, int(r.entity_id))
                if content: name = content.title
            else:
                product = db.session.get(Product, int(r.entity_id))
                if product: name = product.name
                
        results.append({
            "entity_id": r.entity_id,
            "entity_name": name,
            "entity_type": r.entity_type,
            "clicks": "{:,}".format(r.clicks),
        })
    return results

def get_admin_recommendation_health():
    now = datetime.now(timezone.utc)
    last_impression = db.session.scalar(
        select(func.max(RecommendationImpression.created_at))
    )
    
    signals = []
    if last_impression:
        if last_impression.tzinfo is None:
            last_impression = last_impression.replace(tzinfo=timezone.utc)
        hours_since = (now - last_impression).total_seconds() / 3600
        if hours_since > 48:
            signals.append({
                "level": "critical", 
                "message": f"No impressions recorded in the last {int(hours_since)} hours."
            })
    else:
        signals.append({
            "level": "critical", 
            "message": "No impressions ever recorded."
        })
        
    seven_days_ago = now - timedelta(days=7)
    imp_7d = db.session.scalar(
        select(func.count(RecommendationImpression.id))
        .where(RecommendationImpression.created_at >= seven_days_ago)
    ) or 0
    
    click_7d = db.session.scalar(
        select(func.count(RecommendationClick.id))
        .where(RecommendationClick.created_at >= seven_days_ago)
    ) or 0
    
    if imp_7d > 100:
        ctr_7d = (click_7d / imp_7d) * 100
        if ctr_7d < 0.5:
            signals.append({
                "level": "warning", 
                "message": f"7-day overall CTR is dangerously low ({ctr_7d:.2f}%)."
            })
            
    if not signals:
        signals.append({
            "level": "success",
            "message": f"Recommendation system is healthy. {imp_7d} impressions in last 7 days."
        })
        status = "success"
    else:
        status = "critical" if any(s["level"] == "critical" for s in signals) else "warning"
        
    return {
        "status": status,
        "signals": signals
    }

def get_admin_recommendation_trend():
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    imp_stmt = (
        select(
            func.date(RecommendationImpression.created_at).label("day"),
            func.count(RecommendationImpression.id).label("count")
        )
        .where(RecommendationImpression.created_at >= thirty_days_ago)
        .group_by("day")
    )
    
    click_stmt = (
        select(
            func.date(RecommendationClick.created_at).label("day"),
            func.count(RecommendationClick.id).label("count")
        )
        .where(RecommendationClick.created_at >= thirty_days_ago)
        .group_by("day")
    )
    
    imp_rows = db.session.execute(imp_stmt).all()
    click_rows = db.session.execute(click_stmt).all()
    
    data = {}
    for i in range(30, -1, -1):
        day_str = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        data[day_str] = {"impressions": 0, "clicks": 0}
        
    for r in imp_rows:
        day_str = str(r.day)
        if day_str in data:
            data[day_str]["impressions"] = r.count
            
    for r in click_rows:
        day_str = str(r.day)
        if day_str in data:
            data[day_str]["clicks"] = r.count
            
    labels = list(data.keys())
    impressions = [data[d]["impressions"] for d in labels]
    clicks = [data[d]["clicks"] for d in labels]
    
    return {
        "labels": [d[5:] for d in labels],
        "impressions": impressions,
        "clicks": clicks
    }

def get_admin_slot_analysis():
    clicks = db.session.execute(
        select(RecommendationClick)
        .order_by(RecommendationClick.created_at.desc())
        .limit(1000)
    ).scalars().all()
    
    impressions = db.session.execute(
        select(RecommendationImpression)
        .order_by(RecommendationImpression.created_at.desc())
        .limit(3000)
    ).scalars().all()
    
    imp_dict = {}
    for imp in impressions:
        key = (imp.context_id, imp.user_id) if imp.user_id else imp.context_id
        if key not in imp_dict:
            imp_dict[key] = []
        imp_dict[key].append(imp)
        
    slot_counts = {}
    for c in clicks:
        key = (c.context_id, c.user_id) if c.user_id else c.context_id
        imps = imp_dict.get(key, [])
        valid_imps = [i for i in imps if i.created_at <= c.created_at]
        if valid_imps:
            best_imp = valid_imps[0]
            try:
                entity_ids = best_imp.entity_ids
                if isinstance(entity_ids, str):
                    import json
                    entity_ids = json.loads(entity_ids)
                if not entity_ids:
                    continue
                str_ids = [str(eid) for eid in entity_ids]
                if str(c.entity_id) in str_ids:
                    idx = str_ids.index(str(c.entity_id))
                    slot_counts[idx] = slot_counts.get(idx, 0) + 1
            except:
                pass
                
    max_slots = max(slot_counts.keys()) if slot_counts else 0
    limit_slots = min(10, max_slots + 1) if max_slots > 0 else 5
    
    labels = [f"Slot {i+1}" for i in range(limit_slots)]
    data = [slot_counts.get(i, 0) for i in range(limit_slots)]
    
    return {"labels": labels, "data": data}

def get_admin_user_interests_raw(user_id):
    from app.domains.user.models import User
    from app.domains.recommendation.models import UserInterest, UserEntityInterest
    from app.domains.taxonomy.models import Category, Entity
    
    user = db.session.get(User, user_id)
    if not user:
        return None
        
    scores = db.session.execute(
        select(
            UserEntityInterest.entity_id,
            UserEntityInterest.category_id,
            func.sum(UserEntityInterest.score).label("total_score")
        )
        .join(UserInterest, UserEntityInterest.user_interest_id == UserInterest.id)
        .where(UserInterest.user_id == user_id)
        .group_by(UserEntityInterest.entity_id, UserEntityInterest.category_id)
        .order_by(func.sum(UserEntityInterest.score).desc())
        .limit(5)
    ).all()
    
    return (user, scores)

def delete_admin_match(content_id, product_id):
    db.session.execute(
        content_products.delete().where(
            content_products.c.content_id == content_id,
            content_products.c.product_id == product_id,
        )
    )
    db.session.commit()
    return True
