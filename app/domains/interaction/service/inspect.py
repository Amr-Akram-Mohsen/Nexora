from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.extensions import db
from app.domains.interaction.models import Comment, Reaction, ItemClick
from app.domains.item.models import ItemStoreLink, Store, ItemVariant, Item

def get_comment_inspect_metrics(comment_id: int) -> dict:
    stmt = select(Comment).options(
        selectinload(Comment.user),
        selectinload(Comment.content_target),
        selectinload(Comment.item),
        selectinload(Comment.parent),
        selectinload(Comment.replies)
    ).where(Comment.id == comment_id)
    comment = db.session.scalar(stmt)
    
    if not comment:
        return None

    total_user_comments = db.session.scalar(select(func.count(Comment.id)).where(Comment.user_id == comment.user_id)) if comment.user_id else 0

    target_sentiments = db.session.execute(
        select(Comment.sentiment, func.count(Comment.id))
        .where(Comment.target_type == comment.target_type)
        .where(Comment.target_id == comment.target_id)
        .group_by(Comment.sentiment)
    ).all()
    
    recent_reactions = db.session.execute(
        select(Reaction).options(selectinload(Reaction.user))
        .where(Reaction.target_type == 'comment', Reaction.target_id == comment.id)
        .order_by(Reaction.created_at.desc())
        .limit(3)
    ).scalars().all()

    return {
        "comment": comment,
        "total_user_comments": total_user_comments,
        "target_sentiments": target_sentiments,
        "recent_reactions": recent_reactions
    }

def get_link_clicks_metrics(link_id: int) -> dict:
    stmt = (
        select(ItemStoreLink.id.label("link_id"), ItemStoreLink.affiliate_url, Store.name.label("store_name"), Item.name.label("item_name"))
        .select_from(ItemStoreLink)
        .join(Store, ItemStoreLink.store_id == Store.id)
        .join(ItemVariant, ItemStoreLink.variant_id == ItemVariant.id)
        .join(Item, ItemVariant.item_id == Item.id)
        .where(ItemStoreLink.id == link_id)
    )
    link_data = db.session.execute(stmt).mappings().first()
    
    if not link_data:
         return None
         
    total_clicks = db.session.scalar(select(func.count()).select_from(ItemClick).where(ItemClick.item_store_link_id == link_id)) or 0
    latest_click = db.session.scalar(select(func.max(ItemClick.created_at)).where(ItemClick.item_store_link_id == link_id))
    
    country_stats = db.session.execute(
        select(ItemClick.country, func.count(ItemClick.id))
        .where(ItemClick.item_store_link_id == link_id)
        .group_by(ItemClick.country)
        .order_by(func.count(ItemClick.id).desc())
        .limit(5)
    ).all()
    
    referrer_stats = db.session.execute(
        select(ItemClick.referrer, func.count(ItemClick.id))
        .where(ItemClick.item_store_link_id == link_id)
        .where(ItemClick.referrer.isnot(None))
        .where(ItemClick.referrer != "")
        .group_by(ItemClick.referrer)
        .order_by(func.count(ItemClick.id).desc())
        .limit(5)
    ).all()

    return {
        "link_data": link_data,
        "total_clicks": total_clicks,
        "latest_click": latest_click,
        "country_stats": country_stats,
        "referrer_stats": referrer_stats
    }
