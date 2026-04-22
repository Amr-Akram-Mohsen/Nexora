
from app.core.extensions import db
from app.domains.interaction.models import Comment


def delete_comment(comment_id: int) -> bool:
    comment = db.session.get(Comment, comment_id)

    if not comment:
        return False

    db.session.delete(comment)
    db.session.commit()
    return True
