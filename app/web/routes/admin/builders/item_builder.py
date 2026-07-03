from app.web.routes.admin.tables import get_inspect_table
from app.web.routes.admin.helpers import format_date

def build_item_inspect_view_model(aggregated_data: dict) -> dict:
    """Takes aggregated item workflow data and formats it for the UI."""
    dto = aggregated_data["item_dto"]
    engagement_score = aggregated_data["engagement_score"]
    
    variant_groups = [{"label": k.title(), "detail": ", ".join(v)} for k, v in dto["variant_groups"].items()] if dto.get("variant_groups") else None

    data_for_table = {
        "id": dto["id"],
        "name": dto["name"],
        "category": dto["category_name"],
        "brand": dto["brand_name"],
        "source": dto["source_name"],
        "added": format_date(dto["created_at"]) if dto.get("created_at") else None,
        "last synced": format_date(max(dto["last_synced_dates"])) if dto.get("last_synced_dates") else None,
        
        "variants count": dto["variants_count"],
        "store count": dto["store_count"],
        "programs": list(set([lnk["program_name"] for lnk in dto["store_links"] if lnk.get("program_name") and lnk["program_name"] != "—"])),
        "price": dto["min_price"],
        "variant groups": variant_groups or [],
        
        "engagement score": engagement_score,
        "views": dto["view_count"],
        "likes": dto["like_count"],
        "dislikes": dto["dislike_count"],
        "comments": dto["comment_count"],
        "shares": dto["share_count"],
        "saves": dto["save_count"],
        "click count": dto["click_count"],
        
        "linked contents": dto["linked_contents_count"],
        "description": dto["description"],
        "rating": dto["rating"],
        "review count": dto["review_count"],
        "images count": dto["images_count"],
        "specs count": dto["specs_count"],
    }
    
    inspect_table = get_inspect_table("items", data_for_table)

    recent_comments = dto.get("comments", [])
    if recent_comments:
        inspect_table.setdefault("Content & Quality", [])
        for idx, c in enumerate(recent_comments):
            preview = c["content"][:100] + ("..." if len(c["content"]) > 100 else "")
            inspect_table["Content & Quality"].append({
                "label": f"Recent Comment {idx+1}",
                "value": {"label": c["user_name"], "detail": preview},
                "is_labeled": True
            })

    return {
        "inspect_table": inspect_table,
        "store_links": dto["store_links"],
        "variant_summary": dto["variant_summary"],
        "image_strip": dto["image_strip"],
        "specifications": dto["specifications"],
        "distribution_history": aggregated_data["distribution_history"],
        "inspect_id": dto["id"],
        "item_name": dto["name"]
    }

def build_store_inspect_view_model(aggregated_data: dict) -> dict:
    """Takes aggregated data and maps the store DTO to tables.py layout schema."""
    dto = aggregated_data.get("store_dto", aggregated_data)
    data_for_table = {
        "id": dto["id"],
        "name": dto["name"],
        "slug": dto["slug"],
        "website": dto["website"],
        "status": "Active" if dto["is_active"] else "Inactive",
        "affiliate network": dto["affiliate_network"],
        "product count": dto["product_count"],
        "active links": dto["active_links"],
        "avg commission": dto["avg_commission"],
        "country": dto["country"],
        "currency": dto["currency"],
        "api enabled": dto["api_enabled"],
        "total links": dto["total_links"],
        "inactive links": dto["inactive_links"],
        "never synced": dto["never_synced"],
        "stale links (7d)": dto["stale_links"],
        "out of stock": dto["out_of_stock"],
        "avg sync age (days)": dto["avg_sync_age"],
        "last synced at": format_date(dto["last_synced_at"]) if dto.get("last_synced_at") else None,
        "feed enabled": dto["feed_enabled"],
        "network slug": dto["network_slug"],
        "program count": dto["program_count"],
        "avg commission rate": dto["avg_commission"],
        "max commission rate": dto["max_commission"],
        "links with commission": dto["with_commission"],
        "links without commission": dto["without_commission"],
        "links with tracking code": dto["with_tracking"],
        "min price": dto["min_price"],
        "avg price": dto["avg_price"],
        "max price": dto["max_price"],
        "links with discount": dto["with_discount"],
        "avg discount %": dto["avg_discount_pct"],
        "links with null price": dto["null_price"],
        "currency mix": dto["currency_mix"]
    }
    
    return {
        "inspect_table": get_inspect_table("stores", data_for_table),
        "inspect_id": dto["id"]
    }
