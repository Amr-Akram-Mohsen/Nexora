from app.web.routes.admin.tables import get_inspect_table
import urllib.parse

def build_user_inspect_view_model(aggregated_data: dict) -> dict:
    """Takes aggregated user workflow data and formats it for the UI."""
    dto = aggregated_data["user_dto"]
    metrics = dto["metrics"]

    views_count = metrics["views_count"]
    clicks_count = metrics["clicks_count"]
    saves_count = metrics["saves_count"]
    reactions_count = metrics["reactions_count"]
    comments_count = metrics["comments_count"]
    shares_count = metrics["shares_count"]
    recs_seen = metrics["recs_seen"]
    recs_clicked = metrics["recs_clicked"]
    engagement_score = metrics["engagement_score"]

    engagement_breakdown_data = {
        "Views": views_count,
        "Product Clicks": clicks_count,
        "Saves": saves_count,
        "Reactions": reactions_count,
        "Comments": comments_count,
        "Shares": shares_count,
        "Recs Clicked": recs_clicked
    }

    user_email_enc = urllib.parse.quote(dto["email"]) if dto["email"] else ""
    
    reactions_data = {"value": reactions_count, "detail": f"👍 {metrics['likes']}, 👎 {metrics['dislikes']}", "is_number": True}
    comments_data = {"value": comments_count, "detail": f"Pos: {metrics['pos']}, Neu: {metrics['neu']}, Neg: {metrics['neg']}, Spam: {metrics['spam']}", "is_number": True}

    reactions_link = {"value": reactions_data, "link": f'/admin/moderation?reactions_user={user_email_enc}'} if reactions_count > 0 else {"value": "0"}
    comments_link = {"value": comments_data, "link": f'/admin/moderation?comments_user={user_email_enc}'} if comments_count > 0 else {"value": "0"}
    shares_link = {"value": str(shares_count), "link": f'/admin/moderation?shares_user={user_email_enc}'} if shares_count > 0 else {"value": "0"}
    saves_link = {"value": str(saves_count), "link": f'/admin/moderation?saves_user={user_email_enc}'} if saves_count > 0 else {"value": "0"}
    clicks_link = str(clicks_count)

    subscription_status = dto["subscription"].get("status_label", "Not Subscribed")
    if dto["subscription"]["exists"]:
        sub_created = dto["subscription"]["created_at"]
        sub_unsubbed = dto["subscription"]["unsubscribed_at"]

    data_for_table = {
        "id": dto["id"],
        "name": dto["name"],
        "email": dto["email"],
        "role": "Admin" if dto["is_admin"] else "User",
        "subscription": subscription_status,
        "status": "Active" if dto["is_active"] else "Inactive",
        "joined": dto["created_at"],
        "last active": dto["last_login_at"],
        
        "provider": dto["provider"].title() if dto["provider"] else "Local",
        "verified": dto["is_verified"],
        "verified at": dto["verified_at"],
        "verification sent": dto["verification_sent_at"],
        "password changed": dto["password_changed_at"],

        "engagement tier": metrics.get("engagement_tier", "Low"),
        "engagement profile": metrics.get("engagement_profile", "Inactive"),
        "engagement score": engagement_score,
        "views": views_count,
        "reactions": reactions_data,
        "comments": comments_data,
        "saves": saves_count,
        "shares": shares_count,
        "product clicks": clicks_count,
        "recommendations shown": recs_seen,
        "recommendations clicked": recs_clicked,
        
        "recent activity": metrics.get("recent_activity_summary")
    }
    inspect_table = get_inspect_table("users", data_for_table)

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    last_login_at = datetime.fromisoformat(dto["last_login_at"]) if dto["last_login_at"] else None
    days_ago = (now - last_login_at).days if last_login_at and last_login_at.tzinfo else None
    if days_ago is None and last_login_at:
        days_ago = (now.replace(tzinfo=None) - last_login_at).days

    inspect_header = {
        "name": dto["name"] or dto["email"],
        "email": dto["email"],
        "joined": dto["created_at"],
        "last_active": dto["last_login_at"],
        "recency_days": days_ago
    }

    user_interests_data = None
    if dto["interests"] or dto["affinities"].get("Brands"):
        user_interests_data = {
            "products": dto["interests"],
            "affinities": dto["affinities"]
        }

    return {
        "inspect_table": inspect_table,
        "engagement_breakdown": engagement_breakdown_data,
        "user_interests": user_interests_data,
        "inspect_id": dto["id"],
        "inspect_header": inspect_header,
        "user_name": dto["name"] or dto["email"],
        "is_admin": dto["is_admin"],
        "is_active": dto["is_active"]
    }
