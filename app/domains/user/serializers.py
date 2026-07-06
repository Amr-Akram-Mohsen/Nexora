from typing import Optional, Dict, Any

def serialize_user_inspect_dto(user, metrics: dict, brands_map: dict, categories_map: dict, topics_map: dict, items_map: dict, articles_map: dict) -> Optional[Dict[str, Any]]:
    """Serializes a User ORM model, along with their mapped interests and analytics metrics, into a pure DTO."""
    if not user:
        return None

    interests_data = []
    agg_brands = {}
    agg_categories = {}
    agg_topics = {}

    for ui in user.user_interests:
        target_name = f"{ui.target_type.title()} #{ui.target_id}"
        if ui.target_type == 'item' and ui.target_id in items_map:
            target_name = items_map[ui.target_id]
        elif ui.target_type in ('article', 'content') and ui.target_id in articles_map:
            target_name = articles_map[ui.target_id]
        
        item_score = 0
        for s in ui.entity_scores:
            item_score += s.score
            if s.brand_id and s.brand_id in brands_map:
                brand_name = brands_map[s.brand_id]
                agg_brands[brand_name] = agg_brands.get(brand_name, 0) + s.score
            if s.category_id and s.category_id in categories_map:
                cat_name = categories_map[s.category_id]
                agg_categories[cat_name] = agg_categories.get(cat_name, 0) + s.score
            if s.topic_id and s.topic_id in topics_map:
                topic_name = topics_map[s.topic_id]
                agg_topics[topic_name] = agg_topics.get(topic_name, 0) + s.score
        
        interests_data.append({
            "target_name": target_name,
            "target_type": ui.target_type,
            "interaction_count": ui.interaction_count,
            "last_interaction": ui.last_interaction_at.isoformat() if ui.last_interaction_at else None,
            "score": round(item_score, 1)
        })
    
    interests_data.sort(key=lambda x: x["last_interaction"] or "", reverse=True)

    def sort_agg(d):
        return [{"name": k, "score": round(v, 1)} for k, v in sorted(d.items(), key=lambda item: item[1], reverse=True)[:5]]

    aggregated_affinities = {
        "Brands": sort_agg(agg_brands),
        "Categories": sort_agg(agg_categories),
        "Topics": sort_agg(agg_topics)
    }

    sub_is_active = False
    sub_created_at = None
    sub_unsubscribed_at = None
    sub_status_label = "Not Subscribed"
    
    if user.newsletter_subscription:
        sub_is_active = user.newsletter_subscription.is_active
        sub_created_at = user.newsletter_subscription.created_at.isoformat() if user.newsletter_subscription.created_at else None
        sub_unsubscribed_at = user.newsletter_subscription.unsubscribed_at.isoformat() if user.newsletter_subscription.unsubscribed_at else None
        
        if sub_is_active:
            sub_status_label = "Active"
        elif sub_unsubscribed_at:
            sub_status_label = "Unsubscribed"
        else:
            sub_status_label = "Unconfirmed"

    # For recent activity, serialize the latest interaction models
    def serialize_activity(obj):
        if not obj:
            return None
        target_name = getattr(obj, "target", None)
        title = "Unknown"
        if target_name:
            title = getattr(target_name, "title", getattr(target_name, "name", "Comment"))
        
        content = getattr(obj, "content", None)
        return {
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "type": getattr(obj, "type", "action"),
            "target_title": title,
            "content": content
        }

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "provider": user.provider,
        "is_verified": user.is_verified,
        "verified_at": user.verified_at.isoformat() if user.verified_at else None,
        "verification_sent_at": user.verification_sent_at.isoformat() if user.verification_sent_at else None,
        "password_changed_at": user.password_changed_at.isoformat() if user.password_changed_at else None,
        
        "subscription": {
            "exists": user.newsletter_subscription is not None,
            "is_active": sub_is_active,
            "created_at": sub_created_at,
            "unsubscribed_at": sub_unsubscribed_at,
            "status_label": sub_status_label
        },
        
        "interests": interests_data,
        "affinities": aggregated_affinities,
        
        "metrics": {
            "views_count": metrics["views_count"],
            "clicks_count": metrics["clicks_count"],
            "saves_count": metrics["saves_count"],
            "reactions_count": metrics["reactions_count"],
            "comments_count": metrics["comments_count"],
            "shares_count": metrics["shares_count"],
            "recs_seen": metrics["recs_seen"],
            "recs_clicked": metrics["recs_clicked"],
            "engagement_score": metrics["engagement_score"],
            "engagement_tier": metrics["engagement_tier"],
            "engagement_profile": metrics["engagement_profile"],
            "recent_activity_summary": metrics["recent_activity_summary"],
            "likes": metrics["likes"],
            "dislikes": metrics["dislikes"],
            "pos": metrics["pos"],
            "neu": metrics["neu"],
            "neg": metrics["neg"],
            "spam": metrics["spam"],
        },
        
        "recent_activity": {
            "latest_comment": serialize_activity(metrics["latest_comment"]),
            "latest_save": serialize_activity(metrics["latest_save"]),
            "latest_view": serialize_activity(metrics["latest_view"]),
            "latest_reaction": serialize_activity(metrics["latest_reaction"]),
            "latest_share": serialize_activity(metrics["latest_share"]),
            "latest_click": serialize_activity(metrics["latest_click"])
        }
    }
