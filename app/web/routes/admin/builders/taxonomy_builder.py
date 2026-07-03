from app.web.routes.admin.tables import get_inspect_table

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
