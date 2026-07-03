from app.web.routes.admin.tables import get_inspect_table

def build_comment_inspect_view_model(aggregated_data: dict) -> dict:
    dto = aggregated_data["comment_dto"]
    
    total_target_comments = sum(item["count"] for item in dto["sentiment_distribution"])
    sentiment_dist = []
    for item in dto["sentiment_distribution"]:
        count = item["count"]
        pct = (count / total_target_comments * 100) if total_target_comments > 0 else 0
        s_label = item["sentiment"].title() if item["sentiment"] else 'Neutral'
        sentiment_dist.append({"label": s_label, "count": f"{count} ({pct:.1f}%)"})
    
    reactions_html = None
    if dto["recent_reactions"]:
        reactions_html = [{"label": r["user_name"], "detail": r["type"].title()} for r in dto["recent_reactions"]]
        
    latest_replies = None
    if dto["latest_replies"]:
        latest_replies = [{"label": reply} for reply in dto["latest_replies"]]

    data_for_table = {
        "id": dto["id"],
        "comment": dto["content"],
        "sentiment": dto["sentiment"],
        "confidence": round(dto["confidence"], 2) if dto["confidence"] else None,
        "likes": dto["like_count"],
        "dislikes": dto["dislike_count"],
        "shares": dto["share_count"],
        "replies count": dto["replies_count"],
        "recent reactions": reactions_html,
        "user id": dto["user_id"],
        "user name": dto["user_name"],
        "user email": dto["user_email"],
        "total comments": dto["total_user_comments"],
        "parent context": dto["parent_context"],
        "latest replies": latest_replies,
        "target type": dto["target_type"],
        "target title": dto["target_title"],
        "date": dto["created_at"],
        "target comments": total_target_comments,
        "sentiment distribution": sentiment_dist if sentiment_dist else None
    }
    
    inspect_table = get_inspect_table("comments", data_for_table)
    
    actions = [
        {
            "label": "Already Flagged" if dto["sentiment"] == 'spam' else "Flag as Spam",
            "action_type": "toggle-active",
            "icon": "🚩",
            "disabled": True if dto["sentiment"] == 'spam' else False,
            "attrs": {"data-action": "flag-comment", "data-id": dto["id"]}
        },
        {
            "label": "Delete Comment",
            "action_type": "delete",
            "icon": "🗑",
            "extra_class": "inspect-delete-btn",
            "attrs": {"data-action": "delete-comment", "data-id": dto["id"]}
        }
    ]

    return {
        "inspect_table": inspect_table,
        "actions": actions,
        "inspect_id": dto["id"]
    }

def build_link_clicks_view_model(aggregated_data: dict) -> dict:
    dto = aggregated_data["link_clicks_dto"]
    
    top_countries = [{"label": c["country"], "count": c["count"]} for c in dto["country_stats"]] if dto["country_stats"] else None
        
    top_referrers = [{"label": r["referrer"], "count": r["count"]} for r in dto["referrer_stats"]] if dto["referrer_stats"] else None
        
    data = {
        "store name": dto["store_name"],
        "item name": dto["item_name"],
        "total clicks": str(dto["total_clicks"]),
        "latest click": dto["latest_click"][:10] if dto["latest_click"] else None,
        "top countries": {"value": top_countries, "is_list": True} if top_countries else None,
        "top referrers": {"value": top_referrers, "is_list": True} if top_referrers else None
    }
        
    inspect_table = get_inspect_table("clicks", data)
    
    return {
        "inspect_table": inspect_table,
        "actions": []
    }
