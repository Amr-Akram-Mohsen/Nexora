from flask import current_app
from sqlalchemy import select, func
from app.core.extensions import db
from app.domains.interaction.models import Comment, Reaction, View, Save, Share, ProductClick

def _get_weights():
    return {'view': current_app.config.get('ENGAGEMENT_WEIGHT_VIEW', 1.0), 'like': current_app.config.get('ENGAGEMENT_WEIGHT_LIKE', 3.0), 'comment': current_app.config.get('ENGAGEMENT_WEIGHT_COMMENT', 5.0), 'save': current_app.config.get('ENGAGEMENT_WEIGHT_SAVE', 4.0), 'share': current_app.config.get('ENGAGEMENT_WEIGHT_SHARE', 6.0), 'click': current_app.config.get('ENGAGEMENT_WEIGHT_CLICK', 5.0)}

def _get_base_engagement_counts(target_type: str, target_id: int) -> dict:
    views = db.session.scalar(select(func.count()).select_from(View).where(View.target_type == target_type, View.target_id == target_id)) or 0
    likes = db.session.scalar(select(func.count()).select_from(Reaction).where(Reaction.target_type == target_type, Reaction.target_id == target_id, Reaction.type == 'like')) or 0
    comments = db.session.scalar(select(func.count()).select_from(Comment).where(Comment.target_type == target_type, Comment.target_id == target_id)) or 0
    saves = db.session.scalar(select(func.count()).select_from(Save).where(Save.target_type == target_type, Save.target_id == target_id)) or 0
    shares = db.session.scalar(select(func.count()).select_from(Share).where(Share.target_type == target_type, Share.target_id == target_id)) or 0
    return {'views': views, 'likes': likes, 'comments': comments, 'saves': saves, 'shares': shares}

def get_content_engagement_score(content_id: int) -> float:
    weights = _get_weights()
    counts = _get_base_engagement_counts('content', content_id)
    score = counts['views'] * weights['view'] + counts['likes'] * weights['like'] + counts['comments'] * weights['comment'] + counts['saves'] * weights['save'] + counts['shares'] * weights['share']
    return round(score, 1)

def get_item_engagement_score(product_id: int) -> float:
    weights = _get_weights()
    counts = _get_base_engagement_counts('product', product_id)
    from app.domains.product.models import ProductVariant, ProductStoreLink
    clicks = db.session.scalar(select(func.count(ProductClick.id)).join(ProductStoreLink, ProductStoreLink.id == ProductClick.product_store_link_id).join(ProductVariant, ProductVariant.id == ProductStoreLink.variant_id).where(ProductVariant.product_id == product_id)) or 0
    score = counts['views'] * weights['view'] + counts['likes'] * weights['like'] + counts['comments'] * weights['comment'] + counts['saves'] * weights['save'] + counts['shares'] * weights['share'] + clicks * weights['click']
    return round(score, 1)