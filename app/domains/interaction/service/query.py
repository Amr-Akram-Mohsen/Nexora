from app.core.extensions import db, cache
from ..models import View, Reaction, Comment, Save, Share, ProductClick
from sqlalchemy import func, case, select

def get_comment_by_id(comment_id):
    return db.session.get(Comment, comment_id)

def get_comments_for_target(target_type, target_id, parent_id=None):
    query = Comment.query.filter_by(target_type=target_type, target_id=target_id)
    if parent_id is not None:
        query = query.filter_by(parent_id=parent_id)
    else:
        query = query.filter_by(parent_id=None)
    return query.order_by(Comment.created_at.asc()).all()

def check_user_reaction(user_id, target_type, target_id):
    return Reaction.query.filter_by(user_id=user_id, target_type=target_type, target_id=target_id).first()

def check_user_save(user_id, target_type, target_id):
    return Save.query.filter_by(user_id=user_id, target_type=target_type, target_id=target_id).first()

def check_user_reactions_batch(user_id, targets_dict: dict) -> dict:
    results = {}
    for target_type, ids in targets_dict.items():
        if not ids:
            continue
        reactions = Reaction.query.filter(Reaction.user_id == user_id, Reaction.target_type == target_type, Reaction.target_id.in_(ids)).all()
        for r in reactions:
            results[r.target_type, r.target_id] = r.type
    return results

def check_user_saves_batch(user_id, targets_dict: dict) -> dict:
    results = {}
    for target_type, ids in targets_dict.items():
        if not ids:
            continue
        saves = Save.query.filter(Save.user_id == user_id, Save.target_type == target_type, Save.target_id.in_(ids)).all()
        for s in saves:
            results[s.target_type, s.target_id] = True
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

def get_recent_views(user_id, limit=20):
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.core.extensions import db
    return View.query.options(selectinload(View.content), selectinload(View.product)).filter_by(user_id=user_id).order_by(View.created_at.desc()).limit(limit).all()