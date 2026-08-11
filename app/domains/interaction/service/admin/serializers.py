from typing import Optional, Dict, Any
def serialize_comment_inspect_dto(metrics_dict: dict) -> Optional[Dict[str, Any]]:
    if not metrics_dict:
        return None
    comment = metrics_dict['comment']
    target_title = comment.target.title if comment.target_type == 'content' and comment.target else comment.target.name if hasattr(comment.target, 'name') else f'{comment.target_type.capitalize()} #{comment.target_id}'
    parent_context = '—'
    if comment.parent:
        parent_context = comment.parent.content[:60] + ('…' if len(comment.parent.content) > 60 else '')
    latest_replies = []
    if comment.replies:
        sorted_replies = sorted(comment.replies, key=lambda r: r.created_at, reverse=True)
        latest_replies = [f'• {r.content[:40]}...' for r in sorted_replies[:3]]
    target_sentiments = metrics_dict.get('target_sentiments', [])
    sentiment_dist = [{'sentiment': s, 'count': c} for s, c in target_sentiments]
    recent_reactions = metrics_dict.get('recent_reactions', [])
    reactions_data = [{'user_name': r.user.name if r.user else 'User', 'type': r.type} for r in recent_reactions]
    return {'id': comment.id, 'content': comment.content, 'sentiment': comment.sentiment or 'neutral', 'confidence': comment.confidence, 'like_count': comment.like_count, 'dislike_count': comment.dislike_count, 'share_count': comment.share_count, 'replies_count': comment.replies_count, 'user_id': comment.user_id, 'user_name': comment.user.name if comment.user else None, 'user_email': comment.user.email if comment.user else None, 'target_type': comment.target_type, 'target_title': target_title, 'created_at': comment.created_at.isoformat() if comment.created_at else None, 'total_user_comments': metrics_dict.get('total_user_comments', 0), 'parent_context': parent_context, 'latest_replies': latest_replies, 'sentiment_distribution': sentiment_dist, 'recent_reactions': reactions_data}
def serialize_link_clicks_dto(metrics_dict: dict) -> Optional[Dict[str, Any]]:
    if not metrics_dict:
        return None
    link_data = metrics_dict['link_data']
    country_stats = metrics_dict.get('country_stats', [])
    referrer_stats = metrics_dict.get('referrer_stats', [])
    countries = [{'country': c or 'Unknown', 'count': cnt} for c, cnt in country_stats]
    referrers = [{'referrer': r or 'Direct', 'count': cnt} for r, cnt in referrer_stats]
    latest_click = metrics_dict.get('latest_click')
    return {'store_name': link_data['store_name'], 'item_name': link_data['item_name'], 'total_clicks': metrics_dict.get('total_clicks', 0), 'latest_click': latest_click.isoformat() if latest_click else None, 'country_stats': countries, 'referrer_stats': referrers}
def _serialize_comment(c, users, titles_map):
    user = users.get(c.user_id)
    target_title = titles_map.get((c.target_type, c.target_id))
    return {'id': c.id, 'content': c.content, 'preview': c.content[:120] + ('…' if len(c.content) > 120 else ''), 'user_id': c.user_id, 'user_name': user['name'] if user else f'User #{c.user_id}', 'user_email': user['email'] if user else None, 'parent_id': c.parent_id, 'sentiment': c.sentiment or 'neutral', 'confidence': c.confidence, 'target_type': c.target_type, 'target_id': c.target_id, 'like_count': c.like_count, 'dislike_count': c.dislike_count, 'replies_count': c.replies_count, 'replies': c.replies, 'target_title': target_title or f'{c.target_type.capitalize()} #{c.target_id}', 'created_at': c.created_at.isoformat() if c.created_at else None}
def _serialize_reaction(r, users, titles_map):
    user = users.get(r.user_id)
    target_title = titles_map.get((r.target_type, r.target_id))
    if r.target_type == 'content':
        icon = '📄 Content'
    elif r.target_type == 'product':
        icon = '📦 Product'
    else:
        icon = '💬 Comment'
    return {'id': r.id, 'type': r.type, 'user_id': r.user_id, 'username': user['name'] if user else f'User #{r.user_id}', 'user_email': user['email'] if user else None, 'target_type': r.target_type, 'target_icon': icon, 'target_id': r.target_id, 'target_title': target_title or f'{r.target_type.capitalize()} #{r.target_id}', 'created_at': r.created_at.isoformat() if r.created_at else None}
def _serialize_save(s, users, titles_map):
    user = users.get(s.user_id)
    target_title = titles_map.get((s.target_type, s.target_id))
    return {'id': s.id, 'user_id': s.user_id, 'user_name': user['name'] if user else f'User #{s.user_id}', 'user_email': user['email'] if user else None, 'target_type': s.target_type, 'target_id': s.target_id, 'target_title': target_title or f'{s.target_type.capitalize()} #{s.target_id}', 'created_at': s.created_at.isoformat() if s.created_at else None}
def _serialize_share(s, users, titles_map):
    user = users.get(s.user_id)
    target_title = titles_map.get((s.target_type, s.target_id))
    return {'id': s.id, 'user_id': s.user_id, 'user_name': user['name'] if user else f'User #{s.user_id}', 'user_email': user['email'] if user else None, 'target_type': s.target_type, 'target_id': s.target_id, 'target_title': target_title or f'{s.target_type.capitalize()} #{s.target_id}', 'channel': s.channel or '—', 'created_at': s.created_at.isoformat() if s.created_at else None}
def map_comment_for_rows(c):
    return {'id': c['id'], 'title': c['target_title'], 'target_type': c['target_type'], 'preview': c['preview'], 'sentiment': c['sentiment'], 'like_count': c['like_count'], 'dislike_count': c['dislike_count'], 'replies_count': c['replies_count'], 'is_reply': bool(c['parent_id']), 'created_at': c['created_at'][:10] if c['created_at'] else '—', 'username': c['user_name']}
def map_reaction_for_rows(r):
    return {'id': r['id'], 'target': r['target_title'], 'target_type': r['target_icon'], 'reaction_type': r['type'], 'date': r['created_at'][:10] if r['created_at'] else '—', 'username': r['username']}
def map_view_for_rows(v):
    return {'id': f'{v['target_type']}-{v['target_id']}', 'target': v['target_title'], 'target_type': v['target_type'], 'view_count': v['view_count'] or 0, 'auth_views': v['auth_views'] or 0, 'anon_views': v['anon_views'] or 0, 'latest_view': v['latest_view']}
def map_click_for_rows(r):
    return {'id': r['link_id'], 'name': r['item_name'], 'store_name': r['store_name'], 'store_url': r['affiliate_url'], 'click_count': r['click_count'] or 0, 'latest_click': r['latest_click']}
def map_save_for_rows(s):
    return {'id': s['id'], 'target': s['target_title'], 'target_type': s['target_type'], 'username': s['user_name'], 'date': s['created_at'][:10] if s['created_at'] else '—'}
def map_share_for_rows(s):
    return {'id': s['id'], 'user': s['user_name'], 'target': f'{s['target_type'].title()}: {s['target_title']}', 'channel': s['channel'], 'date': s['created_at'][:10] if s['created_at'] else '—'}