from ...models import Content
from sqlalchemy import or_

def get_search_contents(session, query):
    # Contents: search title/description (limit for speed)
    a_query = session.query(Content).filter(
        or_(Content.title.ilike(f'%{query}%'), Content.description.ilike(f'%{query}%'))
    )
    return a_query.order_by(Content.published_at.desc()).limit(50).all()
