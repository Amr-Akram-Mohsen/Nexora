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
    if not obj:
        return None
    type_name = obj.__class__.__name__.lower()
    data = {
        "id": getattr(obj, "id", None),
        "type": type_name,
        "title": getattr(obj, "title", None),
        "preview_text": getattr(obj, "preview_text", None),
        "url": getattr(obj, "url", None),
        "image_url": getattr(obj, "image_url", None) or getattr(obj, "thumbnail_url", None),
        "read_time_minutes": getattr(obj, "read_time_minutes", None),
        "source_name": getattr(obj, "source_name", None),
        "is_content_scraped": getattr(obj, "is_content_scraped", None),
        "content_html": getattr(obj, "content_html", None),
        "body": getattr(obj, "body", None),
        "content_text": getattr(obj, "content_text", None),
        "description": getattr(obj, "description", None),
    }
    return data