from app.domains.serializers import serialize_model, serialize_target

def serialize_content(content_obj, target_obj=None, session=None, include_linked_items=False):
    """
    Serializes a Content model into a predictable dictionary.
    """
    if not content_obj:
        return None

    data = {
        "id": content_obj.id,
        "object_type": content_obj.object_type,
        "section_id": content_obj.section_id,
        "category_id": content_obj.category_id,
        "published_at": content_obj.published_at,
        "is_published": getattr(content_obj, "is_published", True),
        "is_active": getattr(content_obj, "is_active", True),
        "category": serialize_model(content_obj.category)
        if getattr(content_obj, "category", None) and content_obj.category.slug != "uncategorized"
        else None,
        "section": serialize_model(content_obj.section),
        "target": serialize_target(target_obj, session) if target_obj else None,
        "topics": [serialize_model(t) for t in (content_obj.topics or [])],
        "brands": [serialize_model(b) for b in (content_obj.brands or [])],
    }

    if include_linked_items:
        from app.domains.item.service.serializers import serialize_item
        data["linked_items"] = [
            serialize_item(item)
            for item in (getattr(content_obj, "linked_items", None) or [])
        ]

    return data
