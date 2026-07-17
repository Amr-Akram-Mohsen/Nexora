from app.shared.dto.ingestion import RawItemDTO


def map_newsapi_ai(data: dict, region="en"):
    # NewsAPI.ai (formerly Event Registry) format
    articles_data = data.get("articles", {})
    results = articles_data.get("results", []) if isinstance(articles_data, dict) else []
    
    if not isinstance(results, list):
        return []

    products = []
    for a in results:
        if not isinstance(a, dict):
            continue
        a["image_url"] = a.get("image")
        a["source_name"] = (a.get("source") or {}).get("title")
        # Ensure url is present
        a["url"] = a.get("url")
        a["body"] = a.get("body")
        a["word_count"] = len(a["body"].split()) if a.get("body") else 0
        a["content_text"] = None
        a["ingestion_method"] = "newsapi_ai"
        
        # Explicitly set this to None so it isn't incorrectly populated
        a["content_html"] = None
        
        a["published_at"] = a.get("dateTimePub") or a.get("dateTime") or a.get("date")
        a["language"] = a.get("lang")
        a["sentiment_score"] = a.get("sentiment")
        a["authors"] = a.get("authors") or []
        a["quality_score"] = a.get("relevance", 0.0)
        
        # Store non-standard fields here so they aren't lost
        a["extended_metadata"] = {
            "data_type": a.get("dataType"),
            "weight": a.get("wgt"),
            "shares": a.get("shares", {})
        }

        # Extract rich metadata for ingestion
        a["er_concepts"] = a.get("concepts")
        a["er_categories"] = a.get("categories")
        a["er_event_uri"] = a.get("eventUri")
        a["er_event_data"] = a.get("event")
        a["er_location"] = a.get("location")
        a["er_uri"] = a.get("uri")
        a["er_source"] = a.get("source")
            
        products.append(RawItemDTO(**a))
    return products

def map_youtube(data: dict, region="SA"):
    products = data.get("items", [])
    if not isinstance(products, list):
        return []

    results = []

    for product in products:
        if not isinstance(product, dict):
            continue
        video_id = product.get("id", {}).get("videoId")
        if not video_id:
            continue
        snippet = product.get("snippet", {})

        results.append(
            RawItemDTO(
                title=snippet.get("title", ""),
                description=snippet.get("description", ""),
                url=f"https://www.youtube.com/watch?v={video_id}",
                thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url"),
                published_at=snippet.get("publishedAt"),
                channel_name=snippet.get("channelTitle", ""),
                is_video=True,
                region=region,
                external_id=video_id,
                platform="youtube",
            )
        )

    return results

def map_newsapi_event(data: dict) -> dict:
    """
    Safely extracts and formats the event data from NewsAPI AI.
    Handles the nested dictionaries (e.g., {"eng": "Title"}) safely.
    """
    if not data:
        return {}
        
    # The API returns { "eng-12345": { "info": { ... } } } or { "info": { ... } }
    # Try to grab the first value if it's a dict containing "info" or "event"
    first_val = next(iter(data.values())) if data else {}
    if isinstance(first_val, dict) and ("info" in first_val or "event" in first_val or "title" in first_val):
        event_obj = first_val.get("info") or first_val.get("event") or first_val
    else:
        event_obj = data.get("event") or data.get("info") or data
        
    if not isinstance(event_obj, dict):
        return {}

    title_raw = event_obj.get("title")
    title_str = title_raw.get("eng", str(title_raw)) if isinstance(title_raw, dict) else title_raw

    sum_raw = event_obj.get("summary")
    summary_str = sum_raw.get("eng", str(sum_raw)) if isinstance(sum_raw, dict) else sum_raw

    # Extract first available image
    images = event_obj.get("images", [])
    image_url = images[0] if isinstance(images, list) and images else None

    from datetime import datetime
    event_date_str = event_obj.get("eventDate")
    event_date = None
    if event_date_str:
        try:
            event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
        except ValueError:
            pass

    event_type = event_obj.get("type")
    categories = event_obj.get("categories", [])
    if not event_type and categories:
        first_cat = categories[0].get("label", "")
        parts = first_cat.split("/")
        if len(parts) > 1:
            event_type = parts[1]
        else:
            event_type = first_cat

    return {
        "title": title_str,
        "summary": summary_str,
        "event_date": event_date,
        "article_count": event_obj.get("articleCount") or event_obj.get("totalArticleCount", 0),
        "image_url": image_url,
        "event_type": event_type,
        "importance": event_obj.get("importance"), # if available
        "concepts": event_obj.get("concepts", []),
        "categories": categories,
        "location": event_obj.get("location"),
    }
