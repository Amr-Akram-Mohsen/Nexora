from ...models import Article, Content, Post, Video
from sqlalchemy import and_, or_, select
from ..content_access import assign_target_to_contents

def get_search_contents(session_or_query, query=None):
    if query is None:
        from app.core.extensions import db

        session = db.session
        query = session_or_query
    else:
        session = session_or_query

    if not query or not query.strip():
        return []

    from .options import CONTENT_LIST_EAGER_LOADS

    term = f"%{query.strip()}%"
    article_ids = select(Article.id).where(
        or_(
            Article.title.ilike(term),
            Article.description.ilike(term),
            Article.content_text.ilike(term),
            Article.body.ilike(term),
        )
    )
    video_ids = select(Video.id).where(
        or_(Video.title.ilike(term), Video.description.ilike(term))
    )
    post_ids = select(Post.id).where(or_(Post.title.ilike(term), Post.body.ilike(term)))

    contents = (
        session.query(Content)
        .options(*CONTENT_LIST_EAGER_LOADS)
        .filter(Content.is_active, Content.is_published)
        .filter(
            or_(
                and_(
                    Content.object_type == "article",
                    Content.object_id.in_(article_ids),
                ),
                and_(Content.object_type == "video", Content.object_id.in_(video_ids)),
                and_(Content.object_type == "post", Content.object_id.in_(post_ids)),
            )
        )
        .order_by(Content.published_at.desc())
        .limit(50)
        .all()
    )

    return assign_target_to_contents(contents, session)
