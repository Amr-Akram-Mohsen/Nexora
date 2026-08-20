import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.core.extensions import db
from app.shared.constants.core import TargetType
from app.domains.interaction.models import ProductClick
from app.domains.interaction.constants import INTERACTION_TYPE
from app.domains.interaction.service.query import get_recent_views, get_saved_items, get_collection_counts_by_user
from app.domains.interaction.service import (
    react,
    save_item,
    post_comment,
    record_share,
    get_comment_by_id,
    record_view,
    track_recommendation_impression,
    track_recommendation_click,
)
from app.domains.product.service.query import get_items_by_ids
from app.domains.product.models import ProductStoreLink
from app.domains.product.service import get_item_by_id
from app.domains.content.models import Content
from app.domains.content.service.content_access import assign_target_to_contents
from app.domains.content.service.query.filtering import get_contents_by_ids
from app.domains.recommendation.service.interest_service import handle_interaction_interest, handle_comment_interaction
logger = logging.getLogger(__name__)

def get_reading_history_workflow(user_id, limit=20):
    views = get_recent_views(user_id, limit=limit * 2)
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
        contents_map = {c['id']: c for c in serialized_contents}
    items_map = {}
    if product_ids:
        products = get_items_by_ids(product_ids, serialize=True, load='card')
        items_map = {i['id']: i for i in products}
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

def _attach_collection_names(serialized_items: list, saves: list):
    saves_map = {s.target_id: s.collection_name for s in saves}
    for item in serialized_items:
        if item['id'] in saves_map:
            item['collection_name'] = saves_map[item['id']]
    return serialized_items

def get_saved_articles_workflow(user_id):
    saves = get_saved_items(user_id, TargetType.CONTENT)
    if not saves:
        return []
    content_ids = [s.target_id for s in saves]
    contents = get_contents_by_ids(content_ids, session=db.session)
    content_map = {c.id: c for c in contents}
    sorted_contents = [content_map[cid] for cid in content_ids if cid in content_map]
    serialized = assign_target_to_contents(sorted_contents, session=db.session)
    return _attach_collection_names(serialized, saves)

def get_saved_products_workflow(user_id):
    saves = get_saved_items(user_id, TargetType.PRODUCT)
    if not saves:
        return []
    product_ids = [s.target_id for s in saves]
    serialized = get_items_by_ids(product_ids, serialize=True, load='card')
    return _attach_collection_names(serialized, saves)

def get_user_collection_counts_workflow(user_id):
    rows = get_collection_counts_by_user(user_id)
    return [{'name': row.collection_name or 'General', 'count': row.count} for row in rows]

def record_item_click_workflow(link_id, user, ip_address, user_agent, referrer, country):
    link = db.session.get(ProductStoreLink, link_id)
    if not link:
        return None
    user_id = user.id if user and user.is_authenticated else None
    last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    stmt = select(ProductClick).where(ProductClick.product_store_link_id == link.id, ProductClick.created_at >= last_24h, ProductClick.user_id == user_id if user_id else ProductClick.ip_address == ip_address)
    existing = db.session.execute(stmt).scalars().first()
    if not existing:
        click = ProductClick(product_store_link_id=link.id, user_id=user_id, ip_address=ip_address, user_agent=user_agent, referrer=referrer, country=country)
        db.session.add(click)
        link.product.click_count = (link.product.click_count or 0) + 1
        db.session.commit()
    if user and user.is_authenticated:
        handle_interaction_interest(user=user, target=link.product, action='item_click', session=db.session)
    return link.affiliate_url

def track_view_workflow(target_id: int, target_type, user, ip: str) -> dict:
    result = record_view(target_id, target_type, user, ip)
    db.session.commit()
    return result

def _execute_tracking(operation, *args, **kwargs) -> bool:
    success = operation(*args, **kwargs)
    if success:
        db.session.commit()
    else:
        db.session.rollback()
    return success

def track_impression_workflow(entity_type: str, entity_ids: list, context_id: str, user_id: int) -> bool:
    return _execute_tracking(track_recommendation_impression, entity_type, entity_ids, context_id, user_id)

def track_click_workflow(entity_type: str, entity_id: int, context_id: str, user_id: int) -> bool:
    return _execute_tracking(track_recommendation_click, entity_type, entity_id, context_id, user_id)

def handle_interaction_workflow(user, target_type, target_id, interaction_type, reaction_type=None, comment_content=None, comment_id=None, collection_name=None):
    try:
        target = None
        if comment_id:
            target = get_comment_by_id(comment_id)
        else:
            match target_type:
                case TargetType.CONTENT:
                    target = db.session.get(Content, target_id)
                case TargetType.PRODUCT:
                    target = get_item_by_id(target_id, load='minimal')
        if not target:
            return {'success': False, 'error': 'Target not found'}
        result = None
        action = interaction_type
        match interaction_type:
            case INTERACTION_TYPE.REACT:
                result = react(user, 'comment' if comment_id else target_type, comment_id or target_id, reaction_type, target if comment_id else None)
                action = reaction_type
            case INTERACTION_TYPE.SAVE:
                result = save_item(user, target_type, target_id, collection_name=collection_name)
            case INTERACTION_TYPE.COMMENT:
                result = post_comment(user, target_type, target_id, comment_content, comment_id)
            case INTERACTION_TYPE.SHARE:
                result = record_share(user, target_type, target_id)
        if not result:
            return {'success': False, 'error': 'Invalid interaction type'}
        if not result.get('success'):
            return result
        if not comment_id:
            handle_interaction_interest(user=user, target=target, action=action)
            if interaction_type == INTERACTION_TYPE.COMMENT:
                handle_comment_interaction(user=user, target=target, comment_sentiment=result.get('sentiment'))
        db.session.commit()
        return result
    except Exception as e:
        db.session.rollback()
        raise e