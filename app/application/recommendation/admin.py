from app.core.extensions import db
from app.domains.relationships import content_items

def unlink_match_workflow(content_id, item_id):
    db.session.execute(
        content_items.delete().where(
            content_items.c.content_id == content_id,
            content_items.c.item_id == item_id,
        )
    )
    db.session.commit()
    return True
