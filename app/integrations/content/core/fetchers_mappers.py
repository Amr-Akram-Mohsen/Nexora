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
        a["content_text"] = None
        a["ingestion_method"] = "newsapi_ai"
        
        # Explicitly set this to None so it isn't incorrectly populated
        a["content_html"] = None
        
        # Extract rich metadata for ingestion
        a["er_concepts"] = a.get("concepts")
        a["er_categories"] = a.get("categories")
        a["er_event_uri"] = a.get("eventUri")
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
