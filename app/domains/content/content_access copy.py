
from .models import Content, Article, Video, Post
CONTENT_MODEL_MAP = {
    "article": Article,
    "video": Video,
    "post": Post,
}

def resolve_content_object(session, content: Content):
    model = CONTENT_MODEL_MAP.get(content.object_type)
    if not model:
        return None
    return session.get(model, content.object_id)

def create_content(session, *, obj, object_type, published_at, **kwargs):
    content = Content(
        object_type=object_type,
        object_id=obj.id,
        published_at=published_at,
        **kwargs
    )

    session.add(content)
    session.flush()
    return content

def get_or_create_content(session, object_type, external_id, obj_factory):
    model = CONTENT_MODEL_MAP[object_type]

    obj = session.query(model).filter_by(external_id=external_id).first()

    if not obj:
        obj = obj_factory()
        session.add(obj)
        session.flush()

    return obj
