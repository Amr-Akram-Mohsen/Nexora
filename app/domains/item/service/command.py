from app.core.extensions import db
from app.domains.item.models import Item

def delete_item(id: int, session=None) -> bool:
    if session is None:
        session = db.session

    item = session.get(Item, id)

    if not item:
        return False

    session.delete(item)
    return True
