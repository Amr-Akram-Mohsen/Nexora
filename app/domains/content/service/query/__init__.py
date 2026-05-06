from ...models import Content
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from ..content_access import assign_target_to_contents

# Import sub-modules to expose them
from .filtering import get_contents_render, get_filtered_contents
from .trending import get_trending_contents
from .related import get_related_contents
from .search import get_search_contents

def count_contents(session):
    return session.query(Content.id).count()

def get_contents(session, search=None, source=None, rows_count=10):
    query = session.query(Content).order_by(Content.published_at.desc())

    if search and search.strip():
        query = query.filter(or_(Content.title.ilike(f'%{search}%'), Content.description.ilike(f'%{search}%')))

    if rows_count:
        query = query.limit(rows_count)

    return query.all()


def get_content_by_id(session, content_id):
    from app.domains.item.models import Item, ItemVariant, ItemStoreLink
    from .options import CONTENT_EAGER_LOADS
    
    content = session.query(Content).options(
        *CONTENT_EAGER_LOADS,
        selectinload(Content.linked_items)
            .selectinload(Item.variants)
            .selectinload(ItemVariant.store_links)
            .selectinload(ItemStoreLink.store),
        selectinload(Content.linked_items)
            .selectinload(Item.images),
        selectinload(Content.linked_items)
            .selectinload(Item.brand)
    ).get(content_id)
    if not content: return None
    
    serialized = assign_target_to_contents([content], session)
    return serialized[0] if serialized else None

def get_latest_contents(session, limit=100):
    return session.query(Content).order_by(Content.published_at.desc()).limit(limit).all()
