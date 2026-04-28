from ..models import Content
def serialize_content(content: Content, session):
    obj = content.resolve(session)
    if not obj:
        return None

    return {
        "id": content.id,
        "type": content.object_type,
        "title": getattr(obj, "title", None),
        "preview": getattr(obj, "preview_text", None),
        "published_at": content.published_at,
    }
