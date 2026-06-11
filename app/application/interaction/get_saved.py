import logging
from sqlalchemy import select
from app.core.extensions import db
from app.domains.interaction.service.query import get_saved_items
from app.shared.constants.core import TargetType
from app.domains.item.service.query import get_items_by_ids
from app.domains.content.models import Content
from app.domains.content.service.content_access import assign_target_to_contents
from app.domains.content.service.query.options import CONTENT_LIST_EAGER_LOADS

logger = logging.getLogger(__name__)

def get_saved_articles_workflow(user_id):
    """
    Retrieves and serializes all saved contents for a user.
    Uses batch loading to avoid N+1 queries.
    """
    saves = get_saved_items(user_id, TargetType.CONTENT)
    if not saves:
        return []
    
    content_ids = [s.target_id for s in saves]
    
    # Load all contents with eager loads in a single query
    stmt = (
        select(Content)
        .options(*CONTENT_LIST_EAGER_LOADS)
        .where(Content.id.in_(content_ids))
    )
    contents = db.session.execute(stmt).scalars().all()
    
    # Sort contents to match the order of saves (newest saved first)
    content_map = {c.id: c for c in contents}
    sorted_contents = [content_map[cid] for cid in content_ids if cid in content_map]
    
    # Batch resolve polymorphic targets
    return assign_target_to_contents(sorted_contents, session=db.session)

def get_saved_products_workflow(user_id):
    """
    Retrieves and serializes all saved products for a user.
    Uses batch loading to avoid N+1 queries.
    """
    saves = get_saved_items(user_id, TargetType.ITEM)
    if not saves:
        return []
    
    item_ids = [s.target_id for s in saves]
    
    # Load all items and serialize with all card relations eager loaded
    return get_items_by_ids(item_ids, serialize=True, load="card")
