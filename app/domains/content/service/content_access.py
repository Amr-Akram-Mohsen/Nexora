from sqlalchemy import select, func, or_
from app.core.extensions import db
from app.shared.utils.orm_helpers import get_model_registry, resolve_polymorphic_targets
from app.domains.content.serializers import serialize_content_card, serialize_content_detail, serialize_content
from app.domains.serialization_utils import safe_attr
from ..models import Content
from app.domains.relationships import ArticleSource

def resolve_content_object(content, session=None):
    session = session or db.session
    model = get_model_registry().get(content.object_type)
    if not model:
        return None
    return session.get(model, content.object_id)

def resolve(content, session=None):
    return resolve_content_object(content, session=session)

def assign_target_to_contents(contents, include_linked_items=False, session=None, active_filters=None, mode='card'):
    if not contents:
        return contents
    session = session or db.session
    targets_map = resolve_polymorphic_targets(contents, type_attr='object_type', id_attr='object_id', session=session)
    result = []
    for c in contents:
        target_obj = targets_map.get((c.object_type, c.object_id))
        if mode == 'detail':
            result.append(serialize_content_detail(c, target_obj, session, include_linked_items, active_filters=active_filters))
        elif mode == 'card':
            result.append(serialize_content_card(c, target_obj, session, include_linked_items, active_filters=active_filters))
        else:
            result.append(serialize_content(c, target_obj, session, include_linked_items, active_filters=active_filters))
    return result

def create_content(obj, object_type, published_at, session=None, **kwargs):
    session = session or db.session
    stmt = select(Content).where(Content.object_type == object_type, Content.object_id == obj.id)
    existing = session.execute(stmt).scalars().first()
    if existing:
        changed = False
        if existing.published_at != published_at:
            existing.published_at = published_at
            changed = True
        for k, v in kwargs.items():
            if getattr(existing, k) != v:
                setattr(existing, k, v)
                changed = True
        return (existing, changed)
    content = Content(object_type=object_type, object_id=obj.id, published_at=published_at, title=safe_attr(obj, 'title', ''), preview_text=safe_attr(obj, 'preview_text', ''), **kwargs)
    session.add(content)
    session.flush()
    return (content, False)

def get_or_create_content(object_type, external_id, obj_factory, title_fallback=None, url_fallback=None, session=None, **kwargs):
    model = get_model_registry().get(object_type)
    if not model:
        return (None, False)
    session = session or db.session
    obj = None
    is_new = False
    if external_id and hasattr(model, 'external_id'):
        stmt = select(model).where(model.external_id == external_id)
        obj = session.execute(stmt).scalars().first()
    if not obj and url_fallback:
        canonical_url = kwargs.get('canonical_url')
        if object_type == 'article':
            urls_to_check = [u for u in (url_fallback, canonical_url) if u]
            if urls_to_check:
                stmt_url = select(ArticleSource).where(ArticleSource.url.in_(urls_to_check))
                res = session.execute(stmt_url).scalars().first()
                if res:
                    obj = session.get(model, res.article_id)
                elif canonical_url:
                    stmt_art = select(model).where(model.canonical_url == canonical_url)
                    obj = session.execute(stmt_art).scalars().first()
        elif hasattr(model, 'url'):
            stmt_url = select(model).where(model.url == url_fallback)
            obj = session.execute(stmt_url).scalars().first()
    if not obj and title_fallback and hasattr(model, 'title'):
        normalized_title = title_fallback.lower().strip()
        stmt_title = select(model).where(func.lower(model.title) == normalized_title)
        obj = session.execute(stmt_title).scalars().first()
    if not obj:
        obj = obj_factory()
        session.add(obj)
        session.flush()
        is_new = True
    return (obj, is_new)