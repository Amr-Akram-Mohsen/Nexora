from functools import lru_cache
@lru_cache
def get_target_map():
    from app.domains.content.models import Content
    from app.domains.item.models import Item
    return {
        "content": Content,
        "item": Item,
    }

def resolve_target(session, target_type, target_id):
    model = get_target_map().get(target_type)
    if not model:
        return None
    return session.get(model, target_id)

