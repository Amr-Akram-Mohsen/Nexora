from app.domains.interaction.service import react, save_item, post_comment, get_comment_by_id
from app.domains.interaction.constants import INTERACTION_TYPE
from app.domains.content.service import get_content_by_id
from app.domains.item.service import get_item_by_id
from app.domains.recommendation.interest_service import handle_interaction_interest, handle_comment_interaction
from app.shared.constants.core import TargetType
from app.core.extensions import db

def handle_interaction_workflow(user, target_type, target_id, interaction_type, reaction_type=None, comment_content=None, comment_id=None):
    """
    Orchestrates a user interaction (react, save, comment).
    """
    target = None
    if comment_id:
        target = get_comment_by_id(comment_id)
    elif target_type == TargetType.ARTICLE:
        target = get_content_by_id(target_id)
    elif target_type == TargetType.ITEM:
        target = get_item_by_id(target_id)

    if not target:
        return {"success": False, "error": "Target not found"}

    result = None
    action = interaction_type
    
    if interaction_type == INTERACTION_TYPE.REACT:
        if comment_id:
            result = react(user, 'comment', comment_id, reaction_type, target)
        else:
            result = react(user, target_type, target_id, reaction_type)
        action = reaction_type
    elif interaction_type == INTERACTION_TYPE.SAVE:
        result = save_item(user, target_type, target_id)
    elif interaction_type == INTERACTION_TYPE.COMMENT:
        result = post_comment(
            user,
            target_type,
            target_id,
            comment_content,
            comment_id
        )

    if not result.get("success"):
        return result

    # Post-interaction logic (tracking)
    if not comment_id:
        handle_interaction_interest(user=user, target=target, action=action)
        if interaction_type == INTERACTION_TYPE.COMMENT:
            target.comment_count = (target.comment_count or 0) + 1
            handle_comment_interaction(user=user, target=target, comment_sentiment=result.get("sentiment"))
    
    db.session.commit()
    return result
