from app.core.extensions import db
from sqlalchemy import select

def get_model_registry():
    """Returns a map of entity_type strings to their corresponding SQLAlchemy models."""
    from app.domains.content.models import Article, Video, Post, Content
    from app.domains.product.models import Product
    from app.domains.user.models import User
    from app.domains.interaction.models import Comment
    
    return {
        "article": Article,
        "video": Video,
        "post": Post,
        "content": Content,
        "product": Product,
        "user": User,
        "comment": Comment,
    }

def resolve_polymorphic_targets(products, type_attr="target_type", id_attr="target_id", session=None):
    """
    Batch loads polymorphic target objects.
    Returns a dictionary mapping (type, id) -> ORM object.
    """
    if session is None:
        session = db.session

    ids_by_type = {}
    for product in products:
        obj_type = getattr(product, type_attr, None)
        obj_id = getattr(product, id_attr, None)
        if obj_type and obj_id:
            ids_by_type.setdefault(obj_type, set()).add(obj_id)

    targets_map = {}
    model_map = get_model_registry()

    for obj_type, ids in ids_by_type.items():
        model = model_map.get(obj_type)
        if not model:
            continue

        stmt = select(model).where(model.id.in_(list(ids)))
        if obj_type == "article":
            from app.domains.relationships import ArticleSource
            from sqlalchemy.orm import selectinload, joinedload
            stmt = stmt.options(
                joinedload(model.primary_source).joinedload(ArticleSource.source),
                selectinload(model.article_sources).selectinload(ArticleSource.source),
            )

        objs = session.execute(stmt).scalars().all()
        for obj in objs:
            targets_map[(obj_type, obj.id)] = obj

    return targets_map

def resolve_polymorphic_titles(products, type_attr="target_type", id_attr="target_id", session=None):
    """
    Batch loads title/name representation of polymorphic targets.
    Returns a dictionary mapping (type, id) -> String.
    """
    if session is None:
        session = db.session

    ids_by_type = {}
    for product in products:
        # Handling for dictionaries as well as objects
        obj_type = product.get(type_attr) if isinstance(product, dict) else getattr(product, type_attr, None)
        obj_id = product.get(id_attr) if isinstance(product, dict) else getattr(product, id_attr, None)
        if obj_type and obj_id:
            ids_by_type.setdefault(obj_type, set()).add(obj_id)

    titles_map = {}
    model_map = get_model_registry()

    for obj_type, ids in ids_by_type.items():
        model = model_map.get(obj_type)
        if not model:
            continue

        mapper = getattr(model, "__mapper__", None)
        title_col = None
        if mapper:
            if "title" in mapper.columns:
                title_col = model.title
            elif "name" in mapper.columns:
                title_col = model.name
            elif "content" in mapper.columns:
                title_col = model.content  # e.g. Comment

        if title_col is not None:
            stmt = select(model.id, title_col).where(model.id.in_(list(ids)))
            rows = session.execute(stmt).all()
            for r in rows:
                title = r[1]
                if obj_type == "comment" and title:
                    title = title[:60] + ("…" if len(title) > 60 else "")
                titles_map[(obj_type, r[0])] = title

    return titles_map

def resolve_users(products, user_id_attr="user_id", session=None):
    """
    Batch loads basic user information.
    Returns a dictionary mapping user_id -> dict of user data.
    """
    from app.domains.user.models import User
    if session is None:
        session = db.session
        
    user_ids = set()
    for product in products:
        uid = product.get(user_id_attr) if isinstance(product, dict) else getattr(product, user_id_attr, None)
        if uid:
            user_ids.add(uid)
            
    if not user_ids:
        return {}
        
    rows = session.execute(select(User.id, User.name, User.email).where(User.id.in_(user_ids))).mappings().all()
    return {r["id"]: dict(r) for r in rows}
