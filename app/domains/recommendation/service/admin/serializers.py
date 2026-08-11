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
    from app.core.extensions import db
    from app.domains.taxonomy.models import Category, Entity
    affinities = []
    for row in scores:
        name = 'Unknown'
        if getattr(row, 'entity_id', None):
            entity = db.session.get(Entity, row.entity_id)
            if entity:
                if entity.entity_type == 'brand' or entity.origin == 'legacy_brand':
                    name = f'Brand: {entity.name}'
                else:
                    name = f'Topic: {entity.name}'
            else:
                name = f'Entity #{row.entity_id}'
        elif getattr(row, 'category_id', None):
            category = db.session.get(Category, row.category_id)
            name = f'Category: {category.name}' if category else f'Category #{row.category_id}'
        affinities.append({'name': name, 'score': round(row.total_score, 3)})
    return {'user_id': user.id, 'user_name': user.name, 'affinities': affinities}