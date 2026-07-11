import logging
from app.core.extensions import db
from app.domains.interaction.service.query import get_recent_views
from app.shared.constants.core import TargetType
from app.domains.product.service.query import get_items_by_ids
from app.domains.content.service.content_access import assign_target_to_contents
from app.domains.content.service.query.filtering import get_contents_by_ids

logger = logging.getLogger(__name__)

def get_reading_history_workflow(user_id, limit=20):
    """
    Retrieves and serializes the recently viewed contents and products for a user.
    """
    views = get_recent_views(user_id, limit=limit * 2) # Fetch more to account for duplicates
    if not views:
        return []
        
    seen = set()
    unique_views = []
    
    for v in views:
        key = (v.target_type, v.target_id)
        if key not in seen:
            seen.add(key)
            unique_views.append(v)
            if len(unique_views) >= limit:
                break
                
    content_ids = [v.target_id for v in unique_views if v.target_type == TargetType.CONTENT]
    product_ids = [v.target_id for v in unique_views if v.target_type == TargetType.PRODUCT]
    
    contents_map = {}
    if content_ids:
        contents = get_contents_by_ids(content_ids, session=db.session)
        serialized_contents = assign_target_to_contents(contents, session=db.session)
        contents_map = {c["id"]: c for c in serialized_contents}
        
    items_map = {}
    if product_ids:
        products = get_items_by_ids(product_ids, serialize=True, load="card")
        items_map = {i["id"]: i for i in products}
        
    history = []
    for v in unique_views:
        if v.target_type == TargetType.CONTENT and v.target_id in contents_map:
            content_dict = contents_map[v.target_id].copy()
            content_dict['domain_type'] = 'content'
            history.append(content_dict)
        elif v.target_type == TargetType.PRODUCT and v.target_id in items_map:
            item_dict = items_map[v.target_id].copy()
            item_dict['domain_type'] = 'commercial'
            history.append(item_dict)
            
    return history
