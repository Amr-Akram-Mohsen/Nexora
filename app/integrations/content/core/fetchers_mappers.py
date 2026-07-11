from app.shared.dto.ingestion import RawItemDTO


def map_event_registry(data: dict, region="en"):
    # Event Registry format
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
        a["content_text"] = a.get("body")
        a["ingestion_method"] = "event_registry"
        
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

def map_newsapi(data: dict, region="en"):
    articles = data.get("articles", [])
    if not isinstance(articles, list):
        return []

    products = []

    for a in articles:
        if not isinstance(a, dict):
            continue
        # Map NewsAPI specific fields to standard DTO fields
        a["image_url"] = a.get("urlToImage")
        a["source_name"] = (a.get("source") or {}).get("name")
        products.append(RawItemDTO(**a))

    return products


def map_gnews(data: dict, region="en"):
    articles = data.get("articles", [])
    if not isinstance(articles, list):
        return []

    products = []

    for a in articles:
        if not isinstance(a, dict):
            continue
        # Map NewsAPI specific fields to standard DTO fields
        a["image_url"] = a.get("image")
        a["region"] = region.upper()
        a["source_name"] = (a.get("source") or {}).get("name")
        products.append(RawItemDTO(**a))

    return products


def map_youtube(data: dict, region="SA"):
    products = data.get("products", [])
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


def map_reddit(submissions, subreddit_name):
    MIN_SCORE = 20
    MIN_LENGTH = 80

    _REGION_MAP = {
        "saudiarabia": "SA",
        "dubai": "AE",
        "abudhabi": "AE",
        "emirates": "AE",
    }

    from datetime import datetime

    products = []

    for submission in submissions:
        if submission.score < MIN_SCORE:
            continue
        if submission.is_self and len(submission.selftext) < MIN_LENGTH:
            continue

        url = f"https://www.reddit.com{submission.permalink}"
        description = (
            submission.selftext[:500] if submission.is_self else submission.url
        )
        thumbnail = (
            submission.thumbnail
            if str(submission.thumbnail).startswith("http")
            else None
        )
        region = _REGION_MAP.get(subreddit_name.lower())

        products.append(
            RawItemDTO(
                title=submission.title,
                body=description,
                url=url,
                image_url=thumbnail,
                published_at=datetime.utcfromtimestamp(submission.created_utc),
                author=str(submission.author),
                subreddit=subreddit_name,
                upvotes=submission.score,
                comments_count=submission.num_comments,
                region=region,
                external_id=submission.id,
                platform="reddit",
            )
        )
    return products
