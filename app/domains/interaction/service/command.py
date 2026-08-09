from datetime import datetime, timedelta, timezone
from sqlalchemy import update
from functools import lru_cache
from app.domains.content.models import Content
from app.domains.product.models import Product

from app.core.extensions import db
from ..models import View, Reaction, Comment, Save, Share
from app.domains.recommendation.service.sentiment import analyze_sentiment
from app.shared.constants.core import TargetType

@lru_cache
def get_model_map():
    return {
        "content": Content,
        "product": Product,
        "comment": Comment,
    }


ALLOWED_COUNTER_COLUMNS = {
    "like_count",
    "dislike_count",
    "view_count",
    "save_count",
    "share_count",
    "comment_count",
    "click_count",
    "replies_count",
}

def update_counter_atomic(db, model_class, model_id, column, action="inc", amount=1):
    """
    column_attr should be actual ORM attribute, not string.
    """
    if not hasattr(model_class, column):
        raise ValueError(f"{model_class.__name__} has no column '{column}'")

    column_attr = getattr(model_class, column)

    if action == "inc":
        expr = column_attr + amount
    elif action == "dec":
        expr = column_attr - amount
    else:
        raise ValueError("action must be 'inc' or 'dec'")

    stmt = (
        update(model_class)
        .where(model_class.id == model_id)
        .values({column_attr.key: expr})
    )

    db.session.execute(stmt)

def execute_counter_update(
    db,
    model_type: str,
    model_id: int,
    column: str,
    action: str = "inc",
    amount: int = 1,
):
    """
    Centralized safe executor for all counter updates.
    Handles:
    - model resolution
    - atomic update
    - error handling
    """

    model_class = get_model_map().get(model_type)

    if not model_class:
        raise ValueError(f"Unknown model type: {model_type}")

    if column not in ALLOWED_COUNTER_COLUMNS:
        raise ValueError("Invalid counter column")

    try:
        update_counter_atomic(
            db=db,
            model_class=model_class,
            model_id=model_id,
            column=column,
            action=action,
            amount=amount
        )
        db.session.commit()
        db.session.flush()
    except Exception as e:
        db.rollback()
        raise e

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

    execute_counter_update(
        db=db,
        model_type=target_type,
        model_id=target_id,
        column="view_count"
    )

    return {
        'success': True,
        'status' : "viewed"
    }

def react(user, target_type, target_id, reaction_type, target=None):    
    if reaction_type not in ("like", "dislike"):
        return {"success": False, "error": "Invalid reaction"}
    
    reaction = Reaction.query.filter_by(
        user_id=user.id,
        target_type=target_type,
        target_id=target_id
    ).first()

    if reaction and reaction.type == reaction_type:
        db.session.delete(reaction)            
        execute_counter_update(db, target_type, target_id, f"{reaction_type}_count", "dec")
        return {"success": True, "status": "removed", "reaction_type": reaction_type}

    if reaction:
        execute_counter_update(db, target_type, target_id, f"{reaction.type}_count", "dec")
        reaction.type = reaction_type
        status = "changed"
    else:
        db.session.add(Reaction(user_id=user.id, target_type=target_type, target_id=target_id, type=reaction_type))
        status = "added"

    execute_counter_update(db, target_type, target_id, f"{reaction_type}_count", "inc")
    
    return {"success": True, "status": status, "reaction_type": reaction_type}

def save_item(user, target_type, target_id, collection_name=None):
    collection_name = (collection_name or "General").strip().lower()
    
    existing = Save.query.filter_by(
        user_id=user.id,
        target_type=target_type,
        target_id=target_id,
        collection_name=collection_name
    ).first()

    status = 'saved'

    if existing:
        db.session.delete(existing)
        status = 'unsaved'
    else:
        save = Save(
            user_id=user.id,
            target_type=target_type,
            target_id=target_id,
            collection_name=collection_name
        )
        db.session.add(save)

    action = 'inc' if status == 'saved' else 'dec'

    execute_counter_update(
        db=db,
        model_type=target_type,
        model_id=target_id,
        column="save_count",
        action=action
    )

    return {"success": True, "status": status}

def record_share(user, target_type, target_id, channel=None):
    share = Share(
        user_id=user.id,
        target_type=target_type,
        target_id=target_id,
        channel=(channel or "web")[:50],
    )
    db.session.add(share)
    execute_counter_update(
        db=db,
        model_type=target_type,
        model_id=target_id,
        column="share_count"
    )
    return {"success": True, "status": "shared"}

def post_comment(
    user,
    target_type,
    target_id,
    content,
    parent_id
):
    from app.shared.sanitizer import sanitize_text
    sanitized_content = sanitize_text(content)
    if not sanitized_content:
        return {
            "success": False,
            "error": "Comment cannot be empty"
        }

    if parent_id:
        parent = db.session.get(Comment, parent_id)
        if not parent or parent.target_type != target_type or parent.target_id != target_id:
            return {
                "success": False,
                "error": "Parent comment not found"
            }

    sentiment, confidence = analyze_sentiment(sanitized_content)
    created_at = datetime.now(timezone.utc)
        
    comment = Comment(
        user_id=user.id,
        target_type=target_type,
        target_id=target_id,
        content=sanitized_content,
        created_at=created_at,
        sentiment=sentiment,
        confidence=confidence,
        parent_id=parent_id
    )
    db.session.add(comment)

    if parent_id:
        execute_counter_update(
            db=db,
            model_type="comment",
            model_id=parent_id,
            column="replies_count"
        )
    else:
        execute_counter_update(
            db=db,
            model_type=target_type,
            model_id=target_id,
            column="comment_count"
        )

    return {
        "success": True,
        "sentiment": sentiment,
        "comment_data": comment
    }

