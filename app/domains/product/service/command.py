from app.core.extensions import db
from app.domains.product.models import Product
def delete_item(id: int) -> bool:
    product = db.session.get(Product, id)
    if not product:
        return False
    db.session.delete(product)
    return True