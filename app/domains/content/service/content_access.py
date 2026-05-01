from functools import lru_cache
from app.core.extensions import db
@lru_cache
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

def assign_target_to_contents(contents, session):
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
        if obj_type == 'article':
            query = query.options(db.selectinload(model.sources))
        
        objs = query.all()
        for obj in objs:
            targets_map[(obj_type, obj.id)] = obj

    # Assign targets back to content objects
    for c in contents:
        c.target = targets_map.get((c.object_type, c.object_id))
    
    return contents

def create_content(session, *, obj, object_type, published_at, **kwargs):
    from ..models import Content
    
    # 🔹 Simple deduplication: Check if this object is already linked to a Content entry
    existing = session.query(Content).filter_by(
        object_type=object_type,
        object_id=obj.id
    ).first()

    if existing:
        # Update existing record with latest metadata
        existing.published_at = published_at
        for k, v in kwargs.items():
            setattr(existing, k, v)
        return existing

    content = Content(
        object_type=object_type,
        object_id=obj.id,
        published_at=published_at,
        **kwargs
    )

    session.add(content)
    session.flush()
    return content

def get_or_create_content(session, object_type, external_id, obj_factory, title_fallback=None):
    model = get_model_map().get(object_type)
    if not model:
        return None

    obj = None
    
    # 1. Try Deduplication by external_id (Videos, Posts)
    if external_id and hasattr(model, 'external_id'):
        obj = session.query(model).filter_by(external_id=external_id).first()
    
    # 2. Fallback to Title-based deduplication (Articles, or missing ID)
    if not obj and title_fallback and hasattr(model, 'title'):
        from sqlalchemy import func
        # Normalize title for better matching
        normalized_title = title_fallback.lower().strip()
        obj = session.query(model).filter(func.lower(model.title) == normalized_title).first()

    # 3. Create if still not found
    if not obj:
        obj = obj_factory()
        session.add(obj)
        session.flush()

    return obj
