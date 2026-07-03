from typing import Optional, Dict, Any

def serialize_comment_inspect_dto(metrics_dict: dict) -> Optional[Dict[str, Any]]:
    if not metrics_dict:
        return None
        
    comment = metrics_dict["comment"]
    
    target_title = comment.target.title if comment.target_type == 'content' and comment.target else (comment.target.name if hasattr(comment.target, 'name') else f"{comment.target_type.capitalize()} #{comment.target_id}")
    
    parent_context = "—"
    if comment.parent:
        parent_context = comment.parent.content[:60] + ("…" if len(comment.parent.content) > 60 else "")

    latest_replies = []
    if comment.replies:
        sorted_replies = sorted(comment.replies, key=lambda r: r.created_at, reverse=True)
        latest_replies = [f"• {r.content[:40]}..." for r in sorted_replies[:3]]

    target_sentiments = metrics_dict.get("target_sentiments", [])
    sentiment_dist = [{"sentiment": s, "count": c} for s, c in target_sentiments]
    
    recent_reactions = metrics_dict.get("recent_reactions", [])
    reactions_data = [{"user_name": r.user.name if r.user else 'User', "type": r.type} for r in recent_reactions]

    return {
        "id": comment.id,
        "content": comment.content,
        "sentiment": comment.sentiment or "neutral",
        "confidence": comment.confidence,
        "like_count": comment.like_count,
        "dislike_count": comment.dislike_count,
        "share_count": comment.share_count,
        "replies_count": comment.replies_count,
        
        "user_id": comment.user_id,
        "user_name": comment.user.name if comment.user else None,
        "user_email": comment.user.email if comment.user else None,
        
        "target_type": comment.target_type,
        "target_title": target_title,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        
        "total_user_comments": metrics_dict.get("total_user_comments", 0),
        "parent_context": parent_context,
        "latest_replies": latest_replies,
        "sentiment_distribution": sentiment_dist,
        "recent_reactions": reactions_data
    }

def serialize_link_clicks_dto(metrics_dict: dict) -> Optional[Dict[str, Any]]:
    if not metrics_dict:
        return None
        
    link_data = metrics_dict["link_data"]
    country_stats = metrics_dict.get("country_stats", [])
    referrer_stats = metrics_dict.get("referrer_stats", [])
    
    countries = [{"country": c or 'Unknown', "count": cnt} for c, cnt in country_stats]
    referrers = [{"referrer": r or 'Direct', "count": cnt} for r, cnt in referrer_stats]
    
    latest_click = metrics_dict.get("latest_click")
    
    return {
        "store_name": link_data["store_name"],
        "item_name": link_data["item_name"],
        "total_clicks": metrics_dict.get("total_clicks", 0),
        "latest_click": latest_click.isoformat() if latest_click else None,
        "country_stats": countries,
        "referrer_stats": referrers
    }
