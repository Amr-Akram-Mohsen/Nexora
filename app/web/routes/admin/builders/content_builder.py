from app.web.routes.admin.tables import get_inspect_table
from app.web.routes.admin.helpers import format_datetime

def build_content_inspect_view_model(aggregated_data: dict) -> dict:
    """
    Takes the aggregated workflow data and formats it for the UI,
    including calling get_inspect_table and building HTML link structures.
    """
    dto = aggregated_data["content_dto"]
    
    sec_slug = dto["section"]["slug"] if dto.get("section") else None
    cat_slug = dto["category"]["slug"] if dto.get("category") else None
    sec_name = dto["section"]["name"] if dto.get("section") else None
    cat_name = dto["category"]["name"] if dto.get("category") else None

    taxonomy_breadcrumb = []
    if sec_name and sec_slug:
        taxonomy_breadcrumb.append({"label": sec_name, "link": f"/admin/contents?section={sec_slug}"})
    if cat_name and cat_slug:
        taxonomy_breadcrumb.append({"label": cat_name, "link": f"/admin/contents?category={cat_slug}"})

    data_for_table = {
        "id": f"#{dto['id']}",
        "title": dto['title'],
        "type": dto['object_type'],
        "taxonomy path": {"value": taxonomy_breadcrumb, "is_breadcrumb": True} if taxonomy_breadcrumb else None,
        "engagement score": str(aggregated_data["engagement_score"]),
        "related brands": ", ".join(dto.get('brands', [])),
        "related topics": ", ".join(dto['topics']) if dto.get('topics') else None,
        "mentioned products": ", ".join(i['name'] for i in dto['linked_items']) if dto.get('linked_items') else None,
        "attributes": ", ".join(dto['attributes']) if dto.get('attributes') else None,
        "available sources": ", ".join(dto['sources']) if dto.get('sources') else None,
        "primary source": dto['source']['name'] if dto.get('source') else None,
        "acquired via": dto['ingestion_origin'],
        
        # Formatting dates for UI
        "published at": format_datetime(dto.get('published_at')) if dto.get('published_at') else None,
        "ingested at": format_datetime(dto.get('ingested_at')) if dto.get('ingested_at') else None,
        
        "enrichment status": dto['enrichment_status'],
        "status": "Live Index" if dto['is_published'] else "Draft",
        "rendering status": "Active" if dto['is_active'] else "Inactive",
        
        "views": "{:,}".format(dto['view_count'] or 0),
        "likes": "{:,}".format(dto['like_count'] or 0),
        "dislikes": "{:,}".format(dto['dislike_count'] or 0),
        "comments": "{:,}".format(dto['comment_count'] or 0),
        "shares": "{:,}".format(dto['share_count'] or 0),
        "saves": "{:,}".format(dto['save_count'] or 0),
        
        "intent": dto['intent'],
        "gender": dto['gender'],
        "price tier": dto['price_tier'],
        "base score": str(dto['score'] or 0),
        "review score": str(dto['review_score'] or 0),
    }

    if dto['object_type'] == "video":
        data_for_table["platform"] = dto.get('platform')
        data_for_table["channel"] = dto.get('channel_name')
    elif dto['object_type'] == "post":
        data_for_table["platform"] = dto.get('platform')
        data_for_table["author"] = dto.get('author')
        data_for_table["subreddit"] = dto.get('subreddit')
        data_for_table["platform upvotes"] = str(dto.get('upvotes') or 0)
        data_for_table["platform comments"] = str(dto.get('platform_comments_count') or 0)
    elif dto['object_type'] == "article":
        data_for_table["is scraped"] = "Yes" if dto.get('is_content_scraped') else "No"
        data_for_table["word count"] = "{:,}".format(dto.get('word_count') or 0)
        data_for_table["read time"] = f"{dto.get('read_time_minutes')} min" if dto.get('read_time_minutes') else None
        data_for_table["article quality score"] = str(dto.get('article_quality_score') or 0)
        data_for_table["last enrichment attempt"] = format_datetime(dto.get('last_enrichment_attempt')) if dto.get('last_enrichment_attempt') else None

    inspect_table = get_inspect_table("contents", data_for_table)

    if dto.get('original_url'):
        inspect_table.setdefault("Related Metadata", []).append({
            "label": "Source Link",
            "value": {"label": "View Original Link", "link": dto['original_url'], "external": True},
            "is_link": True,
        })

    recent_comments = dto.get("comments", [])[:3]
    if recent_comments:
        inspect_table.setdefault("Related Metadata", [])
        for idx, c in enumerate(recent_comments):
            preview = c["content"][:100] + ("..." if len(c["content"]) > 100 else "")
            inspect_table["Related Metadata"].append({
                "label": f"Recent Comment {idx + 1}",
                "value": {"label": c["user_name"], "detail": preview},
                "is_labeled": True,
            })

    return {
        "inspect_table": inspect_table,
        "article_sources": aggregated_data["article_sources"],
        "distribution_history": aggregated_data["distribution_history"],
        "inspect_id": dto["id"],
    }
