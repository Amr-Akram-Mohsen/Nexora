from sqlalchemy import select, func, case
from datetime import datetime, timezone, timedelta
from app.core.extensions import db
from app.domains.product.models import Product, Store, ProductStoreLink, ProductVariant
from app.domains.product.models import Product

from app.shared.utils.admin_helpers import delete_model_workflow

def delete_item_workflow(product_id):
    return delete_model_workflow(Product, product_id, 'name')


from app.domains.product.service.admin import get_admin_item_inspect_raw
from app.domains.interaction.service.scoring import get_item_engagement_score
from app.domains.distribution.services import get_distribution_history
from app.domains.product.serializers import serialize_item_inspect_dto

def get_item_inspect_workflow(product_id: int) -> dict:
    product = get_admin_item_inspect_raw(product_id)
    if not product:
        return None
        
    dto = serialize_item_inspect_dto(product)
    engagement_score = get_item_engagement_score(product_id)
    distribution_history = get_distribution_history("product", product_id)
    
    return {
        "item_dto": dto,
        "engagement_score": engagement_score,
        "distribution_history": distribution_history
    }

def get_store_inspect_workflow(store_id: int) -> dict:
    from app.domains.product.service.admin import get_admin_store_inspect_raw
    from app.domains.product.serializers import serialize_store_inspect_dto
    
    raw_result = get_admin_store_inspect_raw(store_id)
    if not raw_result:
        return None
        
    store, stats, product_count, currency_mix_list, avg_sync_age = raw_result
    dto = serialize_store_inspect_dto(store, stats, product_count, currency_mix_list, avg_sync_age)
    
    return {
        "store_dto": dto
    }

