from ...models import Content
from sqlalchemy import or_, select

# Import sub-modules to expose them
from .filtering import get_contents_render, get_filtered_contents
from .trending import get_trending_contents
from .related import get_related_contents

def count_contents(session=None):
    from sqlalchemy import func
    if session is None:
        from app.core.extensions import db
        session = db.session
    return session.execute(select(func.count(Content.id))).scalar() or 0

def get_contents(search=None, source=None, rows_count=10, session=None):
    from .utils import build_content_stmt, fetch_contents
    if session is None:
        from app.core.extensions import db
        session = db.session
    
    stmt = build_content_stmt(active_only=False, published_only=False, eager_load="none")
    stmt = stmt.order_by(Content.published_at.desc())

    if search and search.strip():
        stmt = stmt.where(or_(Content.title.ilike(f'%{search}%'), Content.description.ilike(f'%{search}%')))

    if rows_count:
        stmt = stmt.limit(rows_count)

    return fetch_contents(stmt, session)


def get_content_by_id(content_id=None, session=None):
    from .utils import build_content_stmt, fetch_contents
    from ..content_access import assign_target_to_contents
    
    if session is None:
        from app.core.extensions import db
        session = db.session
        
    stmt = build_content_stmt(active_only=False, published_only=False, eager_load="detail")
    stmt = stmt.where(Content.id == content_id)
    
    contents = fetch_contents(stmt, session)
    if not contents:
        return None
        
    serialized = assign_target_to_contents(contents, session, include_linked_items=True)
    return serialized[0] if serialized else None

def get_latest_contents(limit=100, session=None):
    from .utils import build_content_stmt, fetch_contents
    if session is None:
        from app.core.extensions import db
        session = db.session
    
    stmt = build_content_stmt(active_only=False, published_only=False, eager_load="none")
    stmt = stmt.order_by(Content.published_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    return fetch_contents(stmt, session)

