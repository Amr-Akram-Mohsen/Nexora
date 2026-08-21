from app.core.extensions import db, cache
from ..models import View, Reaction, Comment, Save, Share, ProductClick
from sqlalchemy import func, case, select

def get_comment_by_id(comment_id):
    from sqlalchemy.orm import joinedload
    return db.session.execute(
        select(Comment).options(joinedload(Comment.user)).where(Comment.id == comment_id)
    ).scalar_one_or_none()

def get_comments_for_target(target_type, target_id, parent_id=None):
    from sqlalchemy.orm import joinedload, selectinload
    stmt = (
        select(Comment)
        .options(
            joinedload(Comment.user),
            selectinload(Comment.replies).joinedload(Comment.user)
        )
        .where(Comment.target_type == target_type, Comment.target_id == target_id)
    )
    if parent_id is not None:
        stmt = stmt.where(Comment.parent_id == parent_id)
    else:
        stmt = stmt.where(Comment.parent_id.is_(None))
    return db.session.execute(stmt.order_by(Comment.created_at.asc())).scalars().all()

def check_user_reaction(user_id, target_type, target_id):
    return Reaction.query.filter_by(user_id=user_id, target_type=target_type, target_id=target_id).first()

def check_user_save(user_id, target_type, target_id):
    return Save.query.filter_by(user_id=user_id, target_type=target_type, target_id=target_id).first()

def check_user_reactions_batch(user_id, targets_dict: dict) -> dict:
    results = {}
    from sqlalchemy import select, or_
    conditions = []
    for target_type, ids in targets_dict.items():
        if ids:
            conditions.append((Reaction.target_type == target_type) & (Reaction.target_id.in_(ids)))
    if not conditions:
        return results
    reactions = db.session.execute(
        select(Reaction.target_type, Reaction.target_id, Reaction.type)
        .where(Reaction.user_id == user_id, or_(*conditions))
    ).all()
    for r in reactions:
        results[r[0], r[1]] = r[2]
    return results

def check_user_saves_batch(user_id, targets_dict: dict) -> dict:
    results = {}
    from sqlalchemy import select, or_
    conditions = []
    for target_type, ids in targets_dict.items():
        if ids:
            conditions.append((Save.target_type == target_type) & (Save.target_id.in_(ids)))
    if not conditions:
        return results
    saves = db.session.execute(
        select(Save.target_type, Save.target_id)
        .where(Save.user_id == user_id, or_(*conditions))
    ).all()
    for s in saves:
        results[s[0], s[1]] = True
    return results

def get_saved_items(user_id, target_type):
    from sqlalchemy.orm import selectinload
    if target_type == 'content':
        return Save.query.options(selectinload(Save.content)).filter_by(user_id=user_id, target_type='content').order_by(Save.created_at.desc()).all()
    else:
        return Save.query.options(selectinload(Save.product)).filter_by(user_id=user_id, target_type='product').order_by(Save.created_at.desc()).all()

def get_collection_counts_by_user(user_id):
    from sqlalchemy import func
    return db.session.query(Save.collection_name, func.count(Save.id).label('count')).filter(Save.user_id == user_id).group_by(Save.collection_name).all()

def get_user_collections_list(user_id):
    rows = get_collection_counts_by_user(user_id)
    return [{'name': row.collection_name or 'General', 'count': row.count} for row in rows]

def get_recent_views(user_id, limit=20):
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.core.extensions import db
    return View.query.options(selectinload(View.content), selectinload(View.product)).filter_by(user_id=user_id).order_by(View.created_at.desc()).limit(limit).all()