from functools import lru_cache

@lru_cache
def get_model_map():
    from .models import Article, Video, Post
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

def create_content(session, *, obj, object_type, published_at, **kwargs):
    from .models import Content
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
    model = get_model_map().get(object_type)
    if not model:
        return None

    obj = session.query(model).filter_by(external_id=external_id).first()

    if not obj:
        obj = obj_factory()
        session.add(obj)
        session.flush()

    return obj
