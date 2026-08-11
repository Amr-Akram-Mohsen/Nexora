from sqlalchemy import select
from app.domains.product.models import Product
from app.core.extensions import db
def get_item_eager_loads(mode='card'):
    from .options import get_item_load_options
    if mode is None or mode == 'none':
        return []
    if isinstance(mode, (list, tuple)):
        return list(mode)
    return get_item_load_options(mode)
def build_item_stmt(eager_load='card'):
    stmt = select(Product)
    loads = get_item_eager_loads(eager_load)
    if loads:
        stmt = stmt.options(*loads)
    return stmt
def fetch_items(stmt):
    return db.session.execute(stmt).scalars().all()
def fetch_item(stmt):
    return db.session.execute(stmt).scalars().first()