from app.core.extensions import db
from sqlalchemy import select, func, or_

def get_model_map():
    from ..models import Article, Video, Post

    return {
        "article": Article,
        "video": Video,
        "post": Post,
    }


def resolve_content_object(content, session=None):
    if session is None:
        session = db.session
    model = get_model_map().get(content.object_type)
    if not model:
        return None
    return session.get(model, content.object_id)


def resolve(content, session=None):
    return resolve_content_object(content, session=session)


def assign_target_to_contents(contents, include_linked_items=False, session=None, active_filters=None):
    if not contents:
        return contents

    if session is None:
        session = db.session

    from app.shared.utils.orm_helpers import resolve_polymorphic_targets
    targets_map = resolve_polymorphic_targets(
        contents, type_attr="object_type", id_attr="object_id", session=session
    )

    from app.domains.content.serializers import serialize_content

    result = []
    # Assign targets back to content objects
    for c in contents:
        target_obj = targets_map.get((c.object_type, c.object_id))
        result.append(serialize_content(c, target_obj, session, include_linked_items, active_filters=active_filters))

    return result


def create_content(obj, object_type, published_at, session=None, **kwargs):
    from ..models import Content

    if session is None:
        session = db.session

    # 🔹 Simple deduplication: Check if this object is already linked to a Content entry
    stmt = select(Content).where(
        Content.object_type == object_type, Content.object_id == obj.id
    )
    existing = session.execute(stmt).scalars().first()

    if existing:
        changed = False
        # Update existing record with latest metadata
        if existing.published_at != published_at:
            existing.published_at = published_at
            changed = True

        for k, v in kwargs.items():
            if getattr(existing, k) != v:
                setattr(existing, k, v)
                changed = True
        return existing, changed

    content = Content(
        object_type=object_type,
        object_id=obj.id,
        published_at=published_at,
        title=getattr(obj, "title", ""),
        preview_text=getattr(obj, "preview_text", ""),
        **kwargs
    )

    session.add(content)
    session.flush()
    return content, False


def get_or_create_content(
    object_type,
    external_id,
    obj_factory,
    title_fallback=None,
    url_fallback=None,
    session=None,
    **kwargs,
):
    model = get_model_map().get(object_type)
    if not model:
        return None, False

    if session is None:
        session = db.session

    obj = None
    is_new = False

    # 1. Try Deduplication by external_id (Videos, Posts)
    if external_id and hasattr(model, "external_id"):
        stmt = select(model).where(model.external_id == external_id)
        obj = session.execute(stmt).scalars().first()

    # 2. Try Deduplication by url (Articles or models with url)
    if not obj and url_fallback:
        canonical_url = kwargs.get("canonical_url")

        if object_type == "article":
            from app.domains.relationships import ArticleSource

            urls_to_check = [u for u in (url_fallback, canonical_url) if u]
            if urls_to_check:
                # Check all known URLs simultaneously
                stmt_url = select(ArticleSource).where(ArticleSource.url.in_(urls_to_check))
                res = session.execute(stmt_url).scalars().first()

                if res:
                    obj = session.get(model, res.article_id)
                elif canonical_url:
                    # Fallback to checking the article canonical URL directly if no source matched
                    stmt_art = select(model).where(model.canonical_url == canonical_url)
                    obj = session.execute(stmt_art).scalars().first()
        elif hasattr(model, "url"):
            stmt_url = select(model).where(model.url == url_fallback)
            obj = session.execute(stmt_url).scalars().first()

    # 3. Fallback to Title-based deduplication (If missing ID and URL)
    if not obj and title_fallback and hasattr(model, "title"):
        # Normalize title for better matching
        normalized_title = title_fallback.lower().strip()
        stmt_title = select(model).where(func.lower(model.title) == normalized_title)
        obj = session.execute(stmt_title).scalars().first()

    # 4. Create if still not found
    if not obj:
        obj = obj_factory()
        session.add(obj)
        session.flush()
        is_new = True

    return obj, is_new
