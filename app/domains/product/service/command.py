from app.core.extensions import db
from app.domains.product.models import Product

def delete_item(id: int, session=None) -> bool:
    if session is None:
        session = db.session

    product = session.get(Product, id)

    if not product:
        return False

    session.delete(product)
    return True
