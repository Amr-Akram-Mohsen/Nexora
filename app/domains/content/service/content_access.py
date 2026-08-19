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

from .command import create_content, get_or_create_content

__all__ = [
    "resolve_content_object",
    "resolve",
    "assign_target_to_contents",
    "create_content",
    "get_or_create_content",
]