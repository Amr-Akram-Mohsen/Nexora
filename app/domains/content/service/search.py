from sqlalchemy import func, select
from app.domains.content.models import Content
from .content_access import assign_target_to_contents

def build_content_search_vector(content):
    return (
        func.setweight(
            func.to_tsvector(
                "english",
                func.coalesce(
                    content.title,
                    ""
                )
            ),
            "A"
        ).op("||")(
            func.setweight(
                func.to_tsvector(
                    "english",
                    func.coalesce(
                        content.preview_text,
                        ""
                    )
                ),
                "B"
            )
        ).op("||")(
            func.setweight(
                func.to_tsvector(
                    "english",
                    func.coalesce(
                        content.search_text,
                        ""
                    )
                ),
                "C"
            )
        )
    )
    

def populate_content_search_fields(content, obj, object_type):
    """
    Populate denormalized search fields for Content.
    """

    source = ""

    if object_type == "video":
        source = getattr(
            obj,
            "channel_name",
            ""
        ) or ""

    elif object_type == "post":
        source = " ".join(
            filter(
                None,
                [
                    getattr(obj, "author", ""),
                    getattr(obj, "subreddit", "")
                ]
            )
        )
        
    elif object_type == "article":
        source = " ".join(
            filter(
                None,
                [
                    getattr(obj, "author", ""),
                    getattr(obj, "source_name", "")
                ]
            )
        )
    
    canonical = getattr(obj, "canonical_url", "")

    brand_names = " ".join(
        brand.name
        for brand in content.brands
    )

    topic_names = " ".join(
        topic.name
        for topic in content.topics
    )

    attribute_names = " ".join(
        attr.name
        for attr in content.attributes
    )

    category_name = (
        content.category.name
        if content.category
        else ""
    )

    gender_name = (
        content.gender.name
        if content.gender
        else ""
    )

    intent_name = (
        content.intent.name
        if content.intent
        else ""
    )

    price_tier_name = (
        content.price_tier.name
        if content.price_tier
        else ""
    )

    content.search_text = " ".join(
        filter(
            None,
            [
                content.title,
                content.preview_text,

                canonical,
                source,

                brand_names,
                topic_names,
                attribute_names,

                category_name,

                gender_name,
                intent_name,
                price_tier_name,
            ]
        )
    )

    content.search_vector = build_content_search_vector(content)



# def get_search_contents(session_or_query, query=None, limit=80):

#     if query is None:
#         from app.core.extensions import db

#         session = db.session
#         query = session_or_query

#     else:
#         session = session_or_query

#     query = (query or "").strip()

#     if not query:
#         return []

#     from .options import CONTENT_LIST_EAGER_LOADS

#     search_query = func.plainto_tsquery(
#         "english",
#         query
#     )

#     rank = func.ts_rank(
#         Content.search_vector,
#         search_query
#     )

#     contents = (
#         session.query(Content)
#         .options(
#             *CONTENT_LIST_EAGER_LOADS
#         )
#         .filter(
#             Content.is_active,
#             Content.is_published
#         )
#         .filter(
#             Content.search_vector.op("@@")(
#                 search_query
#             )
#         )
#         .order_by(
#             rank.desc(),
#             Content.view_count.desc(),
#             Content.published_at.desc()
#         )
#         .limit(limit)
#         .all()
#     )

#     return assign_target_to_contents(
#         contents,
#         session
#     )

def get_search_contents(
    query,
    limit=80,
    session=None
):
    if session is None:
        from app.core.extensions import db
        session = db.session

    query = (query or "").strip()

    if not query:
        return []

    from .query.options import CONTENT_LIST_EAGER_LOADS

    search_query = func.websearch_to_tsquery(
        "english",
        query
    )

    rank = func.ts_rank_cd(
        Content.search_vector,
        search_query
    )

    stmt = (
        select(Content)
        .options(*CONTENT_LIST_EAGER_LOADS)
        .where(
            Content.is_active,
            Content.is_published,
            Content.search_vector.op("@@")(search_query)
        )
        .order_by(
            rank.desc(),
            Content.view_count.desc(),
            Content.score.desc(),
            Content.published_at.desc()
        )
        .limit(limit)
    )

    contents = session.execute(stmt).scalars().all()

    return assign_target_to_contents(
        contents,
        session=session
    )
