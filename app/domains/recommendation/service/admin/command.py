from app.core.extensions import db
from app.domains.relationships import content_products
def delete_match(content_id: int, product_id: int) -> bool:
    db.session.execute(content_products.delete().where(content_products.c.content_id == content_id, content_products.c.product_id == product_id))
    db.session.commit()
    return True