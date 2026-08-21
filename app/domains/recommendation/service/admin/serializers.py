from typing import Optional, Dict, Any

def serialize_match_inspect_dto(raw_tuple) -> Optional[Dict[str, Any]]:
    if not raw_tuple:
        return None
    content, widget_impressions, unique_users, last_impression, linked_items_stats = raw_tuple
    last_active = last_impression.strftime('%Y-%m-%d %H:%M') if last_impression else 'Never'
    linked_items_data = []
    for product, context_clicks, widget_clicks in linked_items_stats:
        widget_ctr = f'{widget_clicks / widget_impressions * 100:.1f}%' if widget_impressions > 0 else '0.0%'
        affiliate_ctr = f'{context_clicks / content.view_count * 100:.1f}%' if content.view_count and content.view_count > 0 else '0.0%'
        linked_items_data.append({'id': product.id, 'name': product.name or f'Product #{product.id}', 'type': product.product_type, 'clicks': f'{widget_clicks} ({widget_ctr} Widget) | {context_clicks} ({affiliate_ctr} Affiliate) | {product.click_count or 0} Total'})
    return {'content_id': content.id, 'title': content.title or '—', 'type': content.object_type, 'views_count': content.view_count or 0, 'widget_impressions': widget_impressions, 'unique_users_reached': unique_users, 'last_active': last_active, 'linked_items': linked_items_data}

def serialize_user_interests_dto(raw_tuple) -> Optional[Dict[str, Any]]:
    if not raw_tuple:
        return None
    user, scores = raw_tuple
    from sqlalchemy import select
    from app.core.extensions import db
    from app.domains.taxonomy.models import Category, Entity

    entity_ids = [row.entity_id for row in scores if getattr(row, 'entity_id', None)]
    category_ids = [row.category_id for row in scores if getattr(row, 'category_id', None)]

    entity_map = {
        e.id: e for e in db.session.execute(
            select(Entity).where(Entity.id.in_(entity_ids))
        ).scalars().all()
    } if entity_ids else {}

    category_map = {
        c.id: c for c in db.session.execute(
            select(Category).where(Category.id.in_(category_ids))
        ).scalars().all()
    } if category_ids else {}

    affinities = []
    for row in scores:
        name = 'Unknown'
        eid = getattr(row, 'entity_id', None)
        cid = getattr(row, 'category_id', None)
        if eid:
            entity = entity_map.get(eid)
            if entity:
                if entity.entity_type == 'brand' or entity.origin == 'legacy_brand':
                    name = f'Brand: {entity.name}'
                else:
                    name = f'Topic: {entity.name}'
            else:
                name = f'Entity #{eid}'
        elif cid:
            category = category_map.get(cid)
            name = f'Category: {category.name}' if category else f'Category #{cid}'
        affinities.append({'name': name, 'score': round(row.total_score, 3)})
    return {'user_id': user.id, 'user_name': user.name, 'affinities': affinities}