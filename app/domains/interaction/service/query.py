from datetime import datetime, timedelta, timezone
from app.core.extensions import db
from ..models import View, Reaction, Comment, Save, ItemClick
from sqlalchemy import func
from app.domains.recommendation.interest_service import handle_interaction_interest
from app.domains.recommendation.sentiment import analyze_sentiment
from flask import render_template, jsonify

def viewer_filter(query, user, ip_address):
    if user:
        return query.filter(View.user_id == user.id)
    return query.filter(
        View.user_id.is_(None),
        View.ip_address == ip_address
    )

def record_view(
    target,
    target_type,
    user=None,
    ip_address=None
):
    
    if not user and not ip_address:
        return {
            'success': False,
            'error' : "couldn't detect user"
        }
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    query = View.query.filter(
        View.target_type == target_type,
        View.target_id == target.id,
        View.created_at > cutoff
    )

    query = viewer_filter(query, user, ip_address)

    if query.first():
        return {
            'success': False,
            'error' : "already viewed"
        }

    view = View(
        user_id=user.id if user else None,
        ip_address=ip_address,
        target_type=target_type,
        target_id=target.id
    )
    db.session.add(view)

    target.view_count = (target.view_count or 0) + 1
    if user:
      handle_interaction_interest(
          user=user,
          target=target,
          action="view"
      )

    db.session.commit()
    return {
        'success': True,
        'status' : "viewed"
    }

def react(
    user,
    target_type,
    target_id,
    reaction_type,
    target=None
):    
    if reaction_type not in ("like", "dislike"):
        return {
            "success": False,
            "error": "Invalid reaction"
        }
    
    reaction = Reaction.query.filter_by(
        user_id=user.id,
        target_type=target_type,
        target_id=target_id
    ).first()

    status = None

    if reaction:
        if reaction.type == reaction_type:
            db.session.delete(reaction)
            if target:
                if reaction_type == "like":
                    target.likes_count -= 1
                else:
                    target.dislikes_count -= 1
            
            status = 'removed'
        else:
            reaction.type = reaction_type
            if target:
                if reaction_type == "like":
                    target.likes_count += 1
                    target.dislikes_count -= 1
                else:
                    target.dislikes_count += 1
                    target.likes_count -= 1
            status = 'changed'
    else:
        reaction = Reaction(
            user_id=user.id,
            target_type=target_type,
            target_id=target_id,
            type=reaction_type
        )
        db.session.add(reaction)
        if target:
            if reaction_type == "like":
                target.likes_count += 1
            else:
                target.dislikes_count += 1
        status = 'added'
    db.session.flush()
    return {
        "success": True,
        "status": status,
        "reaction_type": reaction_type
    }

def save_item(user, target_type, target_id):
    existing = Save.query.filter_by(
        user_id=user.id,
        target_type=target_type,
        target_id=target_id
    ).first()

    status = 'saved'

    if existing:
        db.session.delete(existing)
        status = 'unsaved'
    else:
        save = Save(
            user_id=user.id,
            target_type=target_type,
            target_id=target_id
        )
        db.session.add(save)

    return {"success": True, "status": status}

def post_comment(
    user,
    target_type,
    target_id,
    content,
    parent_id
):
    # if not content:
    #     return {"success": False, "error": "Empty comment"}

    sentiment, confidence = analyze_sentiment(content)
    created_at = datetime.now(timezone.utc)
        
    comment = Comment(
        user_id=user.id,
        target_type=target_type,
        target_id=target_id,
        content=content,
        created_at=created_at,
        sentiment=sentiment,
        confidence=confidence,
        parent_id=parent_id   # for threaded replies
    )
    db.session.add(comment)
    db.session.flush()  # get comment.id before commit
    return {
        "success": True,
        "sentiment": sentiment,
        "comment": render_template('components/features/comment-card.html', comment=comment, is_reply=parent_id is not None)
    }


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


def get_reaction_stats():
    result = db.session.query(
        Reaction.type,
        func.count(Reaction.id)
    ).group_by(Reaction.type).all()

    stats = {r[0]: r[1] for r in result}

    return {
        "likes": stats.get("like", 0),
        "dislikes": stats.get("dislike", 0)
    }

def get_view_stats():
    total = db.session.query(func.count(View.id)).scalar()

    return {
        "total_views": total or 0
    }

def get_save_stats():
    total = db.session.query(func.count(Save.id)).scalar()

    return {
        "total_saves": total or 0
    }

def get_click_stats():
    total = db.session.query(func.count(ItemClick.id)).scalar()

    return {
        "total_clicks": total or 0
    }


def get_interactions_breakdown():
    return {
        "comments": db.session.query(Comment.id).count(),
        "reactions": db.session.query(Reaction.id).count(),
        "views": db.session.query(View.id).count(),
        "saves": db.session.query(Save.id).count(),
        "clicks": db.session.query(ItemClick.id).count(),
    }


def count_interactions():
    return (
        db.session.query(Comment.id).count()
        + db.session.query(Reaction.id).count()
        + db.session.query(View.id).count()
        + db.session.query(Save.id).count()
        + db.session.query(ItemClick.id).count()
    )

def get_comments(rows_count=10):
    query = Comment.query.order_by(Comment.created_at.desc())

    if rows_count:
        query = query.limit(rows_count)

    return query.all()


