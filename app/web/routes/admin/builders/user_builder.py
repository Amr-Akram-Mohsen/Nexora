from app.web.routes.admin.tables import get_inspect_table
import urllib.parse
from app.web.routes.admin.helpers import format_date

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
        "Item Clicks": clicks_count,
        "Saves": saves_count,
        "Reactions": reactions_count,
        "Comments": comments_count,
        "Shares": shares_count,
        "Recs Clicked": recs_clicked
    }

    user_email_enc = urllib.parse.quote(dto["email"]) if dto["email"] else ""
    reactions_str = f"{reactions_count} (👍 {metrics['likes']}, 👎 {metrics['dislikes']})"
    comments_str = f"{comments_count} (Pos: {metrics['pos']}, Neu: {metrics['neu']}, Neg: {metrics['neg']}, Spam: {metrics['spam']})"

    reactions_link = {"value": reactions_str, "link": f'/admin/moderation?reactions_user={user_email_enc}'} if reactions_count > 0 else {"value": "0"}
    comments_link = {"value": comments_str, "link": f'/admin/moderation?comments_user={user_email_enc}'} if comments_count > 0 else {"value": "0"}
    shares_link = {"value": str(shares_count), "link": f'/admin/moderation?shares_user={user_email_enc}'} if shares_count > 0 else {"value": "0"}
    saves_link = {"value": str(saves_count), "link": f'/admin/moderation?saves_user={user_email_enc}'} if saves_count > 0 else {"value": "0"}
    clicks_link = str(clicks_count)

    counts_dict = {
        "Commenter": comments_count,
        "Saver": saves_count,
        "Sharer": shares_count,
        "Clicker": clicks_count,
        "Viewer": views_count
    }
    max_count = max(counts_dict.values()) if any(counts_dict.values()) else 0
    engagement_profile = "Inactive"
    if max_count > 0:
        for profile, count in counts_dict.items():
            if count == max_count:
                engagement_profile = profile
                break

    recent_activity = "—"
    activities = []
    
    act_data = dto["recent_activity"]
    if act_data.get("latest_comment"): activities.append((act_data["latest_comment"]["created_at"], f"Commented: {act_data['latest_comment']['content'][:50]}..."))
    if act_data.get("latest_save"): activities.append((act_data["latest_save"]["created_at"], f"Saved: {act_data['latest_save']['target_title']}"))
    if act_data.get("latest_view"): activities.append((act_data["latest_view"]["created_at"], f"Viewed: {act_data['latest_view']['target_title']}"))
    if act_data.get("latest_reaction"): activities.append((act_data["latest_reaction"]["created_at"], f"Reacted ({act_data['latest_reaction']['type']}): {act_data['latest_reaction']['target_title']}"))
    if act_data.get("latest_share"): activities.append((act_data["latest_share"]["created_at"], f"Shared: {act_data['latest_share']['target_title']}"))
    if act_data.get("latest_click"): activities.append((act_data["latest_click"]["created_at"], f"Clicked Item Link"))

    if activities:
        activities.sort(key=lambda x: x[0], reverse=True)
        recent_activity = activities[0][1]

    engagement_tier = "Power User" if engagement_score >= 200 else ("High" if engagement_score >= 50 else ("Medium" if engagement_score >= 10 else "Low"))

    subscription_status = "Not Subscribed"
    if dto["subscription"]["exists"]:
        sub_status_text = "Active" if dto["subscription"]["is_active"] else ("Unsubscribed" if dto["subscription"]["unsubscribed_at"] else "Unconfirmed")
        sub_created = format_date(dto["subscription"]["created_at"]) if dto["subscription"]["created_at"] else None
        sub_unsubbed = format_date(dto["subscription"]["unsubscribed_at"]) if dto["subscription"]["unsubscribed_at"] else ""
        subscription_status = f"{sub_status_text} (Joined: {sub_created})"
        if sub_unsubbed:
            subscription_status += f" [Unsubbed: {sub_unsubbed}]"

    data_for_table = {
        "id": dto["id"],
        "name": dto["name"],
        "email": dto["email"],
        "role": "Admin" if dto["is_admin"] else "User",
        "subscription": subscription_status,
        "status": "Active" if dto["is_active"] else "Inactive",
        "joined": format_date(dto["created_at"]) if dto["created_at"] else None,
        "last active": format_date(dto["last_login_at"]) if dto["last_login_at"] else None,
        
        "provider": dto["provider"].title() if dto["provider"] else "Local",
        "verified": dto["is_verified"],
        "verified at": format_date(dto["verified_at"]) if dto["verified_at"] else None,
        "verification sent": format_date(dto["verification_sent_at"]) if dto["verification_sent_at"] else None,
        "password changed": format_date(dto["password_changed_at"]) if dto["password_changed_at"] else None,

        "engagement tier": engagement_tier,
        "engagement profile": engagement_profile,
        "engagement score": engagement_score,
        "views": views_count,
        "reactions": reactions_str,
        "comments": comments_str,
        "saves": saves_count,
        "shares": shares_count,
        "item clicks": clicks_count,
        "recommendations shown": recs_seen,
        "recommendations clicked": recs_clicked,
        
        "recent activity": recent_activity
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

    actions = [
        {
            "label": "Demote to User" if dto["is_admin"] else "Promote to Admin",
            "action_type": "toggle-admin",
            "extra_class": "user-action-toggle-admin",
            "attrs": {"data-action": "toggle-admin", "data-id": dto["id"], "data-name": (dto["name"] or dto["email"])}
        },
        {
            "label": "Deactivate Account" if dto["is_active"] else "Activate Account",
            "action_type": "toggle-active",
            "extra_class": "user-action-toggle-active",
            "attrs": {"data-action": "toggle-active", "data-id": dto["id"], "data-is-active": str(dto["is_active"]).lower(), "data-name": (dto["name"] or dto["email"])}
        },
        {
            "label": "Debug Personalization",
            "action_type": "view",
            "icon": "🧠",
            "extra_class": "inspect-action-debug-recs",
            "attrs": {"data-action": "inspect", "data-domain": "recommendations/user_interests", "data-id": dto["id"]}
        },
        {
            "label": "Delete User",
            "action_type": "delete",
            "icon": "🗑",
            "extra_class": "user-action-delete",
            "attrs": {"data-action": "delete-user", "data-id": dto["id"], "data-name": (dto["name"] or dto["email"])}
        }
    ]
    
    user_interests_data = None
    if dto["interests"] or dto["affinities"].get("Brands"):
        user_interests_data = {
            "items": dto["interests"],
            "affinities": dto["affinities"]
        }

    return {
        "inspect_table": inspect_table,
        "engagement_breakdown": engagement_breakdown_data,
        "user_interests": user_interests_data,
        "actions": actions,
        "inspect_id": dto["id"],
        "inspect_header": inspect_header,
        "user_name": dto["name"] or dto["email"]
    }
