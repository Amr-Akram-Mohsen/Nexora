from sqlalchemy import select
from app.domains.item.models import Item
from app.core.extensions import db

def get_item_eager_loads(mode="card"):
    """
    Retrieves eager-loading options based on the specified mode/profile.
    - 'detail': Full detail eager loading.
    - 'card': Eager loading for catalog cards.
    - 'minimal': Eager loading for minimal properties (brand, category).
    - None or 'none': No eager loading.
    - If a list or tuple of options is passed, it is used directly (override).
    """
    from .options import get_item_load_options
    
    if mode is None or mode == "none":
        return []
    if isinstance(mode, (list, tuple)):
        return list(mode)
    return get_item_load_options(mode)

def build_item_stmt(eager_load="card"):
    """
    Constructs a base SQLAlchemy 2.0 select statement for the Item model.
    """
    stmt = select(Item)
    loads = get_item_eager_loads(eager_load)
    if loads:
        stmt = stmt.options(*loads)
    return stmt

def fetch_items(stmt, session=None):
    """
    Executes a select statement and returns a list of Item models.
    """
    if session is None:
        session = db.session
    return session.execute(stmt).scalars().all()

def fetch_item(stmt, session=None):
    """
    Executes a select statement and returns a single Item model or None.
    """
    if session is None:
        session = db.session
    return session.execute(stmt).scalars().first()
