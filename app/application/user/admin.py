from app.core.extensions import db
from app.domains.user.service import deactivate_user as domain_deactivate_user, activate_user as domain_activate_user
from app.domains.user.service.admin import toggle_admin_user as domain_toggle_admin_user, get_admin_user_inspect_raw
from sqlalchemy import select
from app.domains.taxonomy.models import Category, Entity
from app.domains.user.service.analytics import get_user_analytics_metrics
from app.domains.user.serializers import serialize_user_inspect_dto

def get_user_inspect_workflow(user_id: int) -> dict:
    user = get_admin_user_inspect_raw(user_id)
    if not user:
        return None
        
    metrics = get_user_analytics_metrics(user_id)
    
    entity_ids = set()
    category_ids = set()
    for ui in user.user_interests:
        for score in ui.entity_scores:
            if getattr(score, 'entity_id', None): entity_ids.add(score.entity_id)
            if getattr(score, 'category_id', None): category_ids.add(score.category_id)
            
    entities = db.session.execute(select(Entity).where(Entity.id.in_(entity_ids))).scalars() if entity_ids else []
    brands_map = {e.id: e.name for e in entities if e.entity_type == 'brand'}
    topics_map = {e.id: e.name for e in entities if e.entity_type in ['topic', 'tag', 'concept']}
    categories_map = {c.id: c.name for c in db.session.execute(select(Category).where(Category.id.in_(category_ids))).scalars()} if category_ids else {}

    product_ids = {ui.target_id for ui in user.user_interests if ui.target_type == 'product'}
    article_ids = {ui.target_id for ui in user.user_interests if ui.target_type in ('article', 'content')}
    items_map = {}
    articles_map = {}
    if product_ids:
        from app.domains.product.models import Product
        items_map = {i.id: i.name for i in db.session.execute(select(Product).where(Product.id.in_(product_ids))).scalars()}
    if article_ids:
        from app.domains.content.models import Content
        articles_map = {c.id: c.title for c in db.session.execute(select(Content).where(Content.id.in_(article_ids))).scalars()}
        
    dto = serialize_user_inspect_dto(
        user, metrics, brands_map, categories_map, topics_map, items_map, articles_map
    )
    
    return {"user_dto": dto}

from app.shared.utils.admin_helpers import execute_admin_workflow, delete_model_workflow

def deactivate_user_workflow(user_id):
    return execute_admin_workflow(domain_deactivate_user, user_id)

def activate_user_workflow(user_id):
    return execute_admin_workflow(domain_activate_user, user_id)

def toggle_admin_user_workflow(user_id):
    return execute_admin_workflow(domain_toggle_admin_user, user_id)

def delete_subscriber_workflow(sub_id):
    from app.domains.user.models import NewsletterSubscriber
    return delete_model_workflow(NewsletterSubscriber, sub_id)
