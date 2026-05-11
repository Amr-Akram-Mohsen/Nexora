from datetime import datetime

def dt_iso(dt):
    return dt.isoformat() if dt else None

def serialize_brand(b):
    if not b: return None
    return {
        "id": getattr(b, "id", None),
        "name": getattr(b, "name", None),
        "slug": getattr(b, "slug", None),
        "logo_url": getattr(b, "logo_url", None),
    }

def serialize_topic(t):
    if not t: return None
    return {
        "id": getattr(t, "id", None),
        "name": getattr(t, "name", None),
        "slug": getattr(t, "slug", None),
    }

def serialize_category(c):
    if not c: return None
    return {
        "id": getattr(c, "id", None),
        "name": getattr(c, "name", None),
        "slug": getattr(c, "slug", None),
    }

def serialize_section(s):
    if not s: return None
    return {
        "id": getattr(s, "id", None),
        "name": getattr(s, "name", None),
        "slug": getattr(s, "slug", None),
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
        "image_url": getattr(obj, "image_url", None) or getattr(obj, "thumbnail_url", None),
    }

    # ── Type-Specific Enrichment ─────────────────────────────────────
    
    if type_name == "article":
        data.update({
            "source_name": obj.source_name,
            "source_url": obj.source_url,
            "read_time_minutes": obj.read_time_minutes,
            "is_content_scraped": getattr(obj, "is_content_scraped", False),
            "content_html": getattr(obj, "content_html", None),
            "content_text": getattr(obj, "content_text", None),
            "body": getattr(obj, "body", None),
            "description": getattr(obj, "description", None),
            "word_count": getattr(obj, "word_count", 0),
        })

    elif type_name == "video":
        data.update({
            "platform": getattr(obj, "platform", "youtube"),
            "external_id": getattr(obj, "external_id", None),
            "channel_name": getattr(obj, "channel_name", "Unknown"),
            "description": getattr(obj, "description", None),
            "thumbnail_url": getattr(obj, "thumbnail_url", None),
        })

    elif type_name == "post":
        data.update({
            "platform": getattr(obj, "platform", "reddit"),
            "external_id": getattr(obj, "external_id", None),
            "author": getattr(obj, "author", "Unknown"),
            "subreddit": getattr(obj, "subreddit", None),
            "upvotes": getattr(obj, "upvotes", 0),
            "body": getattr(obj, "body", None),
        })

    elif type_name == "item":
        data.update({
            "price": getattr(obj, "price", None),
            "currency": getattr(obj, "currency", "USD"), # fallback if not in default_variant
            "rating": getattr(obj, "rating", 0.0),
            "review_count": getattr(obj, "review_count", 0),
            "brand_name": obj.brand.name if hasattr(obj, 'brand') and obj.brand else None,
            "category_name": obj.category.name if hasattr(obj, 'category') and obj.category else None,
            "item_type": getattr(obj, "item_type", None),
            "card_type": getattr(obj, "card_type", "item"),
        })

    return data

def unify_common_attrs(obj, session=None):
    return {
        "title": getattr(obj, "title", None),
    }