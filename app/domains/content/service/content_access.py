from app.core.extensions import db
from app.domains.serializers import (
    serialize_model,
    serialize_target,
)


def get_model_map():
    from ..models import Article, Video, Post

    return {
        "article": Article,
        "video": Video,
        "post": Post,
    }


def resolve_content_object(session, content):
    model = get_model_map().get(content.object_type)
    if not model:
        return None
    return session.get(model, content.object_id)


def resolve(content, session):
    return resolve_content_object(session, content)


def assign_target_to_contents(contents, session, include_linked_items=False):
    if not contents:
        return contents

    # Group IDs by object type
    ids_by_type = {}
    for c in contents:
        ids_by_type.setdefault(c.object_type, set()).add(c.object_id)

    # Fetch all targets in 3 queries
    targets_map = {}
    model_map = get_model_map()
    for obj_type, ids in ids_by_type.items():
        model = model_map.get(obj_type)
        if not model:
            continue

        # Batch fetch for this type
        query = session.query(model).filter(model.id.in_(list(ids)))
        if obj_type == "article":
            from app.domains.relationships import ArticleSource

            query = query.options(
                db.joinedload(model.primary_source).joinedload(ArticleSource.source),
                db.selectinload(model.article_sources).selectinload(
                    ArticleSource.source
                ),
            )

        objs = query.all()
        for obj in objs:
            targets_map[(obj_type, obj.id)] = obj

    serialize_linked_item = None
    if include_linked_items:
        from app.domains.item.service.serializers import serialize_item

        serialize_linked_item = serialize_item

    result = []
    # Assign targets back to content objects
    for c in contents:
        target_obj = targets_map.get((c.object_type, c.object_id))

        data = {
            "id": c.id,
            "object_type": c.object_type,
            "section_id": c.section_id,
            "category_id": c.category_id,
            "published_at": c.published_at,
            "is_published": getattr(c, "is_published", True),
            "is_active": getattr(c, "is_active", True),
            "category": serialize_model(c.category)
            if c.category.slug != "uncategorized"
            else None,
            "section": serialize_model(c.section),
            "target": serialize_target(target_obj, session) if target_obj else None,
            "topics": [serialize_model(t) for t in (c.topics or [])],
            "brands": [serialize_model(b) for b in (c.brands or [])],
        }

        if include_linked_items and serialize_linked_item:
            data["linked_items"] = [
                serialize_linked_item(item)
                for item in (getattr(c, "linked_items", None) or [])
            ]

        result.append(data)

    return result


def create_content(session, *, obj, object_type, published_at, **kwargs):
    from ..models import Content

    # 🔹 Simple deduplication: Check if this object is already linked to a Content entry
    existing = (
        session.query(Content)
        .filter_by(object_type=object_type, object_id=obj.id)
        .first()
    )

    if existing:
        changed = False
        # Update existing record with latest metadata
        if existing.published_at != published_at:
            existing.published_at = published_at
            changed = True

        for k, v in kwargs.items():
            if getattr(existing, k) != v:
                setattr(existing, k, v)
                changed = True
        return existing, changed

    content = Content(
        object_type=object_type, object_id=obj.id, published_at=published_at, **kwargs
    )

    session.add(content)
    session.flush()
    return content, False


def get_or_create_content(
    session,
    object_type,
    external_id,
    obj_factory,
    title_fallback=None,
    url_fallback=None,
    **kwargs,
):
    model = get_model_map().get(object_type)
    if not model:
        return None, False

    obj = None
    is_new = False

    # 1. Try Deduplication by external_id (Videos, Posts)
    if external_id and hasattr(model, "external_id"):
        obj = session.query(model).filter_by(external_id=external_id).first()

    # 2. Try Deduplication by url (Articles or models with url)
    if not obj and url_fallback:
        canonical_url = kwargs.get("canonical_url")

        if object_type == "article":
            from app.domains.relationships import ArticleSource

            # Check primary URL
            res = session.query(ArticleSource).filter_by(url=url_fallback).first()

            # If not found, check if canonical_url matches an existing article's canonical or primary source URL
            if not res and canonical_url:
                # Does canonical_url match any Source URL?
                res = session.query(ArticleSource).filter_by(url=canonical_url).first()

                # Or does it match any Article's stored canonical_url?
                if not res:
                    obj = (
                        session.query(model)
                        .filter_by(canonical_url=canonical_url)
                        .first()
                    )

            if res and not obj:
                obj = session.get(model, res.article_id)
        elif hasattr(model, "url"):
            obj = session.query(model).filter_by(url=url_fallback).first()

    # 3. Fallback to Title-based deduplication (If missing ID and URL)
    if not obj and title_fallback and hasattr(model, "title"):
        from sqlalchemy import func

        # Normalize title for better matching
        normalized_title = title_fallback.lower().strip()
        obj = (
            session.query(model)
            .filter(func.lower(model.title) == normalized_title)
            .first()
        )

    # 4. Create if still not found
    if not obj:
        obj = obj_factory()
        session.add(obj)
        session.flush()
        is_new = True

    return obj, is_new
