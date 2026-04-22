from app.core.extensions import db
from app.domains.item.models import Item


def delete_item(id: int) -> bool:
    item = db.session.get(Item, id)

    if not item:
        return False

    db.session.delete(item)
    db.session.commit()
    return True

