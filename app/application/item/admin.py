from app.core.extensions import db
from app.domains.item.models import Item

def delete_item_workflow(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        return None
    name = item.name
    db.session.delete(item)
    db.session.commit()
    return name
