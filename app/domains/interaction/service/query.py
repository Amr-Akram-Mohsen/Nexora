from app.core.extensions import db
from ..models import View, Reaction, Comment, Save, ItemClick
from sqlalchemy import func

def get_comment_by_id(comment_id):
    return db.session.get(Comment, comment_id)

def get_comments_for_target(target_type, target_id, parent_id=None):
    query = Comment.query.filter_by(
        target_type=target_type,
        target_id=target_id
    )
    if parent_id is not None:
        query = query.filter_by(parent_id=parent_id)
    else:
        query = query.filter_by(parent_id=None)
    
    return query.order_by(Comment.created_at.asc()).all()

def check_user_reaction(user_id, target_type, target_id):
    return Reaction.query.filter_by(
        user_id=user_id,
        target_type=target_type,
        target_id=target_id
    ).first()

def check_user_save(user_id, target_type, target_id):
    return Save.query.filter_by(
        user_id=user_id,
        target_type=target_type,
        target_id=target_id
    ).first()

def get_saved_items(user_id, target_type):
    from sqlalchemy.orm import selectinload
    if target_type == "content":
        return Save.query.options(selectinload(Save.content))\
            .filter_by(user_id=user_id, target_type="content")\
            .order_by(Save.created_at.desc()).all()
    else:
        return Save.query.options(selectinload(Save.item))\
            .filter_by(user_id=user_id, target_type="item")\
            .order_by(Save.created_at.desc()).all()

def count_likes():
    return db.session.query(Reaction.id).filter_by(type="like").count()

def count_dislikes():
    return db.session.query(Reaction.id).filter_by(type="dislike").count()

def count_views():
    return db.session.query(View.id).count()

def count_comments():
    return db.session.query(Comment.id).count()

def count_saves():
    return db.session.query(Save.id).count()

def count_item_clicks():
    return db.session.query(ItemClick.id).count()

def get_interactions_breakdown():
    return {
        "comments": count_comments(),
        "reactions": count_likes() + count_dislikes(),
        "views": count_views(),
        "saves": count_saves(),
        "clicks": count_item_clicks(),
    }

def get_reaction_stats():
    return {
        "likes": count_likes(),
        "dislikes": count_dislikes()
    }

def get_view_stats():
    return {"total": count_views()}

def get_save_stats():
    return {"total": count_saves()}

def get_click_stats():
    return {"total": count_item_clicks()}

def get_all_comments():
    return Comment.query.order_by(Comment.created_at.desc()).all()
