from app.shared.dto.ingestion import RawItemDTO


def map_newsapi(data: dict, region="en"):
    articles = data.get("articles", [])
    if not isinstance(articles, list):
        return []

    items = []

    for a in articles:
        if not isinstance(a, dict):
            continue
        # Map NewsAPI specific fields to standard DTO fields
        a["image_url"] = a.get("urlToImage")
        a["source_name"] = (a.get("source") or {}).get("name")
        items.append(RawItemDTO(**a))

    return items


def map_gnews(data: dict, region="en"):
    articles = data.get("articles", [])
    if not isinstance(articles, list):
        return []

    items = []

    for a in articles:
        if not isinstance(a, dict):
            continue
        # Map NewsAPI specific fields to standard DTO fields
        a["image_url"] = a.get("image")
        a["region"] = region.upper()
        a["source_name"] = (a.get("source") or {}).get("name")
        items.append(RawItemDTO(**a))

    return items


def map_youtube(data: dict, region="SA"):
    items = data.get("items", [])
    if not isinstance(items, list):
        return []

    results = []

    for item in items:
        if not isinstance(item, dict):
            continue
        video_id = item.get("id", {}).get("videoId")
        if not video_id:
            continue
        snippet = item.get("snippet", {})

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

    items = []

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

        items.append(
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
    return items
