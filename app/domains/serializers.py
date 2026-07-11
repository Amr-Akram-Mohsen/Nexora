from datetime import datetime


def serialize_model(m):
    if not m:
        return None
    return {
        "name": getattr(m, "name", None),
        "slug": getattr(m, "slug", None),
    }


def serialize_target(obj, session=None):
    """
    Serializes a polymorphic target object (Article, Video, Post, or Item).
    Ensures all type-specific fields are present for a premium UI.
    """
    if not obj:
        return None

    # Determine type name (e.g., 'article', 'video', 'post', 'item')
    type_name = obj.__class__.__name__.lower()

    # Core fields common to most targets
    data = {
        "id": getattr(obj, "id", None),
        "type": type_name,
        "title": getattr(obj, "title", None) or getattr(obj, "name", None),
        "preview_text": getattr(obj, "preview_text", None),
        "url": getattr(obj, "url", None),
        "image_url": getattr(obj, "image_url", None)
        or getattr(obj, "thumbnail_url", None),
    }

    # ── Type-Specific Enrichment ─────────────────────────────────────

    if type_name == "article":
        data.update(
            {
                "source_name": obj.source_name,
                "source_url": obj.source_url,
                "read_time_minutes": obj.read_time_minutes,
                "images": getattr(obj, "images", None),
                "videos": getattr(obj, "videos", None),
                "extended_metadata": getattr(obj, "extended_metadata", None),
                "author": getattr(obj, "author", None),
                "content_text": getattr(obj, "content_text", None),
                "formatted_paragraphs": getattr(obj, "formatted_paragraphs", []),
                "body": getattr(obj, "body", None),
                "description": getattr(obj, "description", None),
                "word_count": getattr(obj, "word_count", 0),
            }
        )

    elif type_name == "video":
        data.update(
            {
                "platform": getattr(obj, "platform", "youtube"),
                "external_id": getattr(obj, "external_id", None),
                "channel_name": getattr(obj, "channel_name", "Unknown"),
                "description": getattr(obj, "description", None),
                "thumbnail_url": getattr(obj, "thumbnail_url", None),
            }
        )

    elif type_name == "post":
        data.update(
            {
                "platform": getattr(obj, "platform", "reddit"),
                "external_id": getattr(obj, "external_id", None),
                "author": getattr(obj, "author", "Unknown"),
                "subreddit": getattr(obj, "subreddit", None),
                "upvotes": getattr(obj, "upvotes", 0),
                "body": getattr(obj, "body", None),
            }
        )

    elif type_name == "item":
        from app.domains.item.serializers import serialize_item
        
        item_data = serialize_item(obj)
        if item_data:
            data.update(item_data)
            # Unify basic target keys from item_data
            data["title"] = item_data.get("name")
            data["brand_name"] = item_data.get("brand", {}).get("name") if item_data.get("brand") else None
            data["category_name"] = item_data.get("category", {}).get("name") if item_data.get("category") else None

    return data
