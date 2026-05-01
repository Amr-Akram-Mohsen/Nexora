from flask import render_template
from app.domains.interaction.service import get_comments_for_target

def get_comments_html(target_type, target_id, parent_id=None):
    """
    Returns HTML for comments/replies.
    """
    comments = get_comments_for_target(target_type, target_id, parent_id)
    
    comments_html = "".join(
        render_template(
            'components/features/comment-card.html',
            comment=c,
            is_reply=parent_id is not None
        ) for c in comments
    )
    
    return comments_html
