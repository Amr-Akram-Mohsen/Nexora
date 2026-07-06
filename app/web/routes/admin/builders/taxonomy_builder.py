from app.web.routes.admin.tables import get_inspect_table
from app.web.routes.admin.helpers import format_status, format_featured

def build_taxonomy_inspect_view_model(entity, entity_type, metadata) -> dict:
    top_contents = metadata.pop("_top_contents", None)
    top_items = metadata.pop("_top_items", None)
    
    data = {
        "id": f"#{entity.id}",
        "name": entity.name,
        "status": format_status(getattr(entity, "is_active", True)),
        "sort order": str(entity.sort_order) if hasattr(entity, "sort_order") else "0",
    }
    data.update(metadata)
    
    if entity_type == "category":
        data["slug"] = entity.slug
        data["hierarchy level"] = "Leaf" if entity.is_leaf else "Parent"
        if entity.is_leaf and entity.parent:
            data["parent name"] = entity.parent.name
        inspect_table = get_inspect_table("categories", data)
    elif entity_type == "brand":
        data["slug"] = entity.slug
        data["industry"] = entity.industry or "—"
        data["featured"] = format_featured(entity.is_featured)
        inspect_table = get_inspect_table("brands", data)
    elif entity_type == "topic":
        data["slug"] = entity.slug
        data["featured"] = format_featured(entity.is_featured)
        inspect_table = get_inspect_table("topics", data)
    elif entity_type == "section":
        import json
        data["slug"] = entity.slug
        data["description"] = entity.description or "—"
        data["allowed filters"] = json.dumps(entity.allowed_filters) if entity.allowed_filters else "—"
        inspect_table = get_inspect_table("sections", data)
    elif entity_type == "attribute":
        data["slug"] = entity.slug
        data["category"] = entity.category.name if entity.category else "Global"
        inspect_table = get_inspect_table("attributes", data)
    elif entity_type == "gender_facet":
        data["slug"] = entity.slug
        inspect_table = get_inspect_table("gender_facets", data)
    elif entity_type == "intent_facet":
        data["slug"] = entity.slug
        inspect_table = get_inspect_table("intent_facets", data)
    elif entity_type == "price_tier_facet":
        data["slug"] = entity.slug
        inspect_table = get_inspect_table("price_tier_facets", data)
    else:
        inspect_table = {}

    return {
        "inspect_table": inspect_table,
        "top_contents": top_contents,
        "top_items": top_items,
        "domain": f"{entity_type}s"
    }

def build_source_inspect_view_model(aggregated_data: dict) -> dict:
    """Takes aggregated source workflow data and formats it for the UI."""
    dto = aggregated_data["source_dto"]
    
    date_min = dto["date_min"]
    date_max = dto["date_max"]
    date_range = f"{date_min[:10] if date_min else 'Unknown'} to {date_max[:10] if date_max else 'Unknown'}"

    data_for_table = {
        "id": dto["id"],
        "name": dto["name"],
        "slug": dto["slug"],
        "domain": dto["domain"],
        "status": "Active" if dto["is_active"] else "Inactive",
        "authority score": dto["authority_score"],
        "avg quality score": dto["avg_quality_score"],
        "avg word count": dto["avg_word_count"],
        "scrape coverage": f"{dto['scrape_coverage']}%",
        "published date range": date_range,
        
        "channels": dto["channels"],
        "last fetch": dto["last_fetch"][:10] if dto["last_fetch"] else None,
        "success count": dto["success_count"],
        "failure count": dto["failure_count"],
        "consecutive failures": dto["consecutive_failures"],
        
        "article count": dto["article_count"],
        "video count": dto["video_count"],
        "post count": dto["post_count"],
        "categories covered": dto["categories_covered"],
        
        "pending": dto["pipeline_pending"],
        "enriching": dto["pipeline_enriching"],
        "complete": dto["pipeline_complete"],
        "failed": dto["pipeline_failed"],
        
        "total views": dto["total_views"],
        "total likes": dto["total_likes"],
        "total saves": dto["total_saves"],
        "total comments": dto["total_comments"],
        
        "primary attribution count": dto["primary_attribution_count"],
        "secondary attribution count": dto["secondary_attribution_count"]
    }
    
    inspect_table = get_inspect_table("sources", data_for_table)
    
    return {
        "inspect_table": inspect_table,
        "inspect_id": dto["id"],
        "source_header": {
            "name": dto["name"],
            "domain": dto["domain"],
            "logo_url": dto["logo_url"],
            "authority_score": dto["authority_score"],
            "article_count": dto["article_count"]
        },
        "top_articles": dto["top_articles"]
    }
