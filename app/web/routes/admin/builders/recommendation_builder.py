from app.web.routes.admin.tables import get_inspect_table

def build_match_inspect_view_model(aggregated_data: dict) -> dict:
    dto = aggregated_data["match_dto"]
    
    data = {
        "content id": f"#{dto['content_id']}",
        "title": dto["title"],
        "type": dto["type"],
        "views count": str(dto["views_count"]),
        "widget impressions": "{:,}".format(dto["widget_impressions"]),
        "unique users reached": "{:,}".format(dto["unique_users_reached"]),
        "last active": dto["last_active"]
    }
    
    inspect_table = get_inspect_table("recommendations", data)
    
    return {
        "inspect_table": inspect_table,
        "linked_items": dto["linked_items"],
        "inspect_id": dto["content_id"]
    }

def build_user_interests_view_model(aggregated_data: dict) -> dict:
    dto = aggregated_data["user_interests_dto"]
    
    data = {}
    for i, affinity in enumerate(dto["affinities"]):
        data[f"affinity {i+1}"] = {
            "value": {"label": affinity["name"], "detail": f"Score: {affinity['score']}"},
            "is_labeled": True
        }
    
    for i in range(len(dto["affinities"]), 5):
        data[f"affinity {i+1}"] = "—"
        
    inspect_table = get_inspect_table("user_interests", data)
    
    return {
        "inspect_table": inspect_table,
        "actions": []
    }
