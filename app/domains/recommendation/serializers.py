from typing import Optional, Dict, Any

def serialize_match_inspect_dto(raw_tuple) -> Optional[Dict[str, Any]]:
    if not raw_tuple:
        return None
        
    content, widget_impressions, unique_users, last_impression, linked_items_stats = raw_tuple

    last_active = last_impression.strftime("%Y-%m-%d %H:%M") if last_impression else "Never"

    linked_items_data = []
    for item, context_clicks, widget_clicks in linked_items_stats:
        widget_ctr = f"{(widget_clicks / widget_impressions * 100):.1f}%" if widget_impressions > 0 else "0.0%"
        affiliate_ctr = f"{(context_clicks / content.view_count * 100):.1f}%" if content.view_count and content.view_count > 0 else "0.0%"
        
        linked_items_data.append({
            "id": item.id,
            "name": item.name or f"Item #{item.id}",
            "type": item.item_type,
            "clicks": f"{widget_clicks} ({widget_ctr} Widget) | {context_clicks} ({affiliate_ctr} Affiliate) | {item.click_count or 0} Total"
        })

    return {
        "content_id": content.id,
        "title": content.title or "—",
        "type": content.object_type,
        "views_count": content.view_count or 0,
        "widget_impressions": widget_impressions,
        "unique_users_reached": unique_users,
        "last_active": last_active,
        "linked_items": linked_items_data
    }

def serialize_user_interests_dto(raw_tuple) -> Optional[Dict[str, Any]]:
    if not raw_tuple:
        return None
        
    user, scores = raw_tuple
    
    from app.core.extensions import db
    from app.domains.taxonomy.models import Brand, Category, Topic
    
    affinities = []
    for row in scores:
        name = "Unknown"
        if row.brand_id:
            brand = db.session.get(Brand, row.brand_id)
            name = f"Brand: {brand.name}" if brand else f"Brand #{row.brand_id}"
        elif row.category_id:
            category = db.session.get(Category, row.category_id)
            name = f"Category: {category.name}" if category else f"Category #{row.category_id}"
        elif row.topic_id:
            topic = db.session.get(Topic, row.topic_id)
            name = f"Topic: {topic.name}" if topic else f"Topic #{row.topic_id}"
            
        affinities.append({
            "name": name,
            "score": round(row.total_score, 3)
        })
        
    return {
        "user_id": user.id,
        "user_name": user.name,
        "affinities": affinities
    }
