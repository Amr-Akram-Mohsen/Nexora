from datetime import datetime, timedelta, timezone
from flask import render_template
from app.core.extensions import db
from ..models import View, Reaction, Comment, Save
from app.domains.recommendation.sentiment import analyze_sentiment
from .target_access import resolve_target

def viewer_filter(query, user, ip_address):
    if user:
        return query.filter(View.user_id == user.id)
    return query.filter(
        View.user_id.is_(None),
        View.ip_address == ip_address
    )

def record_view(
    target_id,
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
        View.target_id == target_id,
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
        target_id=target_id
    )
    db.session.add(view)

    target = resolve_target(db.session, target_type, target_id)
    if target:
        target.view_count = (target.view_count or 0) + 1
    
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
        parent_id=parent_id
    )
    db.session.add(comment)
    db.session.flush()
    return {
        "success": True,
        "sentiment": sentiment,
        "comment": render_template('components/features/comment-card.html', comment=comment, is_reply=parent_id is not None)
    }

def delete_comment(comment_id: int) -> bool:
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return False
    db.session.delete(comment)
    db.session.commit()
    return True
