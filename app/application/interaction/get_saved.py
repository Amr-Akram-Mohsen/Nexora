import logging
from sqlalchemy import select
from app.core.extensions import db
from app.domains.interaction.service.query import get_saved_items
from app.shared.constants.core import TargetType
from app.domains.product.service.query import get_items_by_ids
from app.domains.content.service.content_access import assign_target_to_contents
from app.domains.content.service.query.filtering import get_contents_by_ids

logger = logging.getLogger(__name__)

def _attach_collection_names(serialized_items: list, saves: list):
    """Helper to attach collection_name from saves to serialized items."""
    saves_map = {s.target_id: s.collection_name for s in saves}
    for item in serialized_items:
        if item["id"] in saves_map:
            item["collection_name"] = saves_map[item["id"]]
    return serialized_items

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
    contents = get_contents_by_ids(content_ids, session=db.session)
    
    # Sort contents to match the order of saves (newest saved first)
    content_map = {c.id: c for c in contents}
    sorted_contents = [content_map[cid] for cid in content_ids if cid in content_map]
    
    # Batch resolve polymorphic targets
    serialized = assign_target_to_contents(sorted_contents, session=db.session)
    
    return _attach_collection_names(serialized, saves)

def get_saved_products_workflow(user_id):
    """
    Retrieves and serializes all saved products for a user.
    Uses batch loading to avoid N+1 queries.
    """
    saves = get_saved_items(user_id, TargetType.PRODUCT)
    if not saves:
        return []
    
    product_ids = [s.target_id for s in saves]
    
    # Load all products and serialize with all card relations eager loaded
    serialized = get_items_by_ids(product_ids, serialize=True, load="card")
    
    return _attach_collection_names(serialized, saves)

def get_user_collection_counts_workflow(user_id):
    """
    Retrieves the count of saved items per collection for a user.
    Uses a direct database aggregation query.
    """
    from app.domains.interaction.service.query import get_collection_counts_by_user
    rows = get_collection_counts_by_user(user_id)
    return [{"name": row.collection_name or "General", "count": row.count} for row in rows]
