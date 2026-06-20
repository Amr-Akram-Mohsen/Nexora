from flask import current_app
from sqlalchemy import select, func
from app.core.extensions import db
from app.domains.interaction.models import Comment, Reaction, View, Save, Share, ItemClick

def _get_weights():
    return {
        "view": current_app.config.get("ENGAGEMENT_WEIGHT_VIEW", 1.0),
        "like": current_app.config.get("ENGAGEMENT_WEIGHT_LIKE", 3.0),
        "comment": current_app.config.get("ENGAGEMENT_WEIGHT_COMMENT", 5.0),
        "save": current_app.config.get("ENGAGEMENT_WEIGHT_SAVE", 4.0),
        "share": current_app.config.get("ENGAGEMENT_WEIGHT_SHARE", 6.0),
        "click": current_app.config.get("ENGAGEMENT_WEIGHT_CLICK", 5.0),
    }

def get_content_engagement_score(content_id: int) -> float:
    weights = _get_weights()
    
    views = db.session.scalar(select(func.count()).select_from(View).where(View.target_type == 'content', View.target_id == content_id)) or 0
    likes = db.session.scalar(select(func.count()).select_from(Reaction).where(Reaction.target_type == 'content', Reaction.target_id == content_id, Reaction.type == 'like')) or 0
    comments = db.session.scalar(select(func.count()).select_from(Comment).where(Comment.target_type == 'content', Comment.target_id == content_id)) or 0
    saves = db.session.scalar(select(func.count()).select_from(Save).where(Save.target_type == 'content', Save.target_id == content_id)) or 0
    shares = db.session.scalar(select(func.count()).select_from(Share).where(Share.target_type == 'content', Share.target_id == content_id)) or 0
    
    score = (
        views * weights["view"] +
        likes * weights["like"] +
        comments * weights["comment"] +
        saves * weights["save"] +
        shares * weights["share"]
    )
    return round(score, 1)

def get_item_engagement_score(item_id: int) -> float:
    weights = _get_weights()
    
    views = db.session.scalar(select(func.count()).select_from(View).where(View.target_type == 'item', View.target_id == item_id)) or 0
    likes = db.session.scalar(select(func.count()).select_from(Reaction).where(Reaction.target_type == 'item', Reaction.target_id == item_id, Reaction.type == 'like')) or 0
    comments = db.session.scalar(select(func.count()).select_from(Comment).where(Comment.target_type == 'item', Comment.target_id == item_id)) or 0
    saves = db.session.scalar(select(func.count()).select_from(Save).where(Save.target_type == 'item', Save.target_id == item_id)) or 0
    shares = db.session.scalar(select(func.count()).select_from(Share).where(Share.target_type == 'item', Share.target_id == item_id)) or 0
    
    from app.domains.item.models import ItemVariant, ItemStoreLink
    clicks = db.session.scalar(
        select(func.count(ItemClick.id))
        .join(ItemStoreLink, ItemStoreLink.id == ItemClick.item_store_link_id)
        .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
        .where(ItemVariant.item_id == item_id)
    ) or 0
    
    score = (
        views * weights["view"] +
        likes * weights["like"] +
        comments * weights["comment"] +
        saves * weights["save"] +
        shares * weights["share"] +
        clicks * weights["click"]
    )
    return round(score, 1)
