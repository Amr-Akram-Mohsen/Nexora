from ...models import Article, Content, Post, Video
from sqlalchemy import and_, or_, select
from ..content_access import assign_target_to_contents

# def get_search_contents(session_or_query, query=None, limit=80):
#     if query is None:
#         from app.core.extensions import db

#         session = db.session
#         query = session_or_query
#     else:
#         session = session_or_query

#     if not query or not query.strip():
#         return []

#     from .options import CONTENT_LIST_EAGER_LOADS

#     from app.domains.system.models import Brand, Category, Section, Topic

#     term = f"%{query}%"
#     article_ids = select(Article.id).where(
#         or_(
#             Article.title.ilike(term),
#             Article.description.ilike(term),
#             Article.content_text.ilike(term),
#             Article.body.ilike(term),
#             Article.canonical_url.ilike(term),
#         )
#     )
#     video_ids = select(Video.id).where(
#         or_(
#             Video.title.ilike(term),
#             Video.description.ilike(term),
#             Video.channel_name.ilike(term),
#         )
#     )
#     post_ids = select(Post.id).where(
#         or_(
#             Post.title.ilike(term),
#             Post.body.ilike(term),
#             Post.subreddit.ilike(term),
#             Post.author.ilike(term),
#         )
#     )

#     contents = (
#         session.query(Content)
#         .options(*CONTENT_LIST_EAGER_LOADS)
#         .filter(Content.is_active, Content.is_published)
#         .filter(
#             or_(
#                 and_(
#                     Content.object_type == "article",
#                     Content.object_id.in_(article_ids),
#                 ),
#                 and_(Content.object_type == "video", Content.object_id.in_(video_ids)),
#                 and_(Content.object_type == "post", Content.object_id.in_(post_ids)),
#                 Content.category.has(
#                     or_(Category.name.ilike(term), Category.slug.ilike(term))
#                 ),
#                 Content.section.has(
#                     or_(Section.name.ilike(term), Section.slug.ilike(term))
#                 ),
#                 Content.topics.any(or_(Topic.name.ilike(term), Topic.slug.ilike(term))),
#                 Content.brands.any(or_(Brand.name.ilike(term), Brand.slug.ilike(term))),
#             )
#         )
#         .order_by(Content.view_count.desc(), Content.published_at.desc())
#         .limit(limit)
#         .all()
#     )

#     return assign_target_to_contents(contents, session)

def get_search_contents(session_or_query, query=None, limit=80):
    if query is None:
        from app.core.extensions import db

        session = db.session
        query = session_or_query
    else:
        session = session_or_query

    if not query or not query.strip():
        return []

    from .options import CONTENT_LIST_EAGER_LOADS

    from app.domains.system.models import Brand, Category, Section, Topic


    article_ids = (
        select(Article.id)
        .where(
            func.to_tsvector(
                "english",
                func.concat(
                    Article.title,
                    " ",
                    Article.description,
                    " ",
                    Article.content_text,
                    " ",
                    Article.canonical_url,
                    " ",
                    Article.body
                )
            ).match(query)
        )
    )

    video_ids = (
        select(Video.id)
        .where(
            func.to_tsvector(
                "english",
                func.concat(
                    Video.title,
                    " ",
                    Video.description,
                    " ",
                    Video.channel_name,
                )
            ).match(query)
        )
    )

    post_ids = (
        select(Post.id)
        .where(
            func.to_tsvector(
                "english",
                func.concat(
                    Post.title,
                    " ",
                    Post.body,
                    " ",
                    Post.subreddit,
                    " ",
                    Post.author,
                )
            ).match(query)
        )
    )

    term = f"%{query}%"

    contents = (
        session.query(Content)
        .options(*CONTENT_LIST_EAGER_LOADS)
        .filter(Content.is_active, Content.is_published)
        .filter(
            or_(
                and_(Content.object_type == "article", Content.object_id.in_(article_ids)),
                and_(Content.object_type == "video", Content.object_id.in_(video_ids)),
                and_(Content.object_type == "post", Content.object_id.in_(post_ids)),
                Content.category.has(
                    or_(Category.name.ilike(term), Category.slug.ilike(term))
                ),
                Content.section.has(
                    or_(Section.name.ilike(term), Section.slug.ilike(term))
                ),
                Content.topics.any(or_(Topic.name.ilike(term), Topic.slug.ilike(term))),
                Content.brands.any(or_(Brand.name.ilike(term), Brand.slug.ilike(term))),
            )
        )
        .order_by(Content.view_count.desc(), Content.published_at.desc())
        .limit(limit)
        .all()
    )

    return assign_target_to_contents(contents, session)


