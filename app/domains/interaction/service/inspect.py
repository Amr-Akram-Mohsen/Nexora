from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.extensions import db
from app.domains.interaction.models import Comment, Reaction, ProductClick
from app.domains.product.models import ProductStoreLink, Store, ProductVariant, Product

def get_comment_inspect_metrics(comment_id: int) -> dict:
    stmt = select(Comment).options(
        selectinload(Comment.user),
        selectinload(Comment.content_target),
        selectinload(Comment.product),
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
        select(ProductStoreLink.id.label("link_id"), ProductStoreLink.affiliate_url, Store.name.label("store_name"), Product.name.label("item_name"))
        .select_from(ProductStoreLink)
        .join(Store, ProductStoreLink.store_id == Store.id)
        .join(ProductVariant, ProductStoreLink.variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .where(ProductStoreLink.id == link_id)
    )
    link_data = db.session.execute(stmt).mappings().first()
    
    if not link_data:
         return None
         
    total_clicks = db.session.scalar(select(func.count()).select_from(ProductClick).where(ProductClick.product_store_link_id == link_id)) or 0
    latest_click = db.session.scalar(select(func.max(ProductClick.created_at)).where(ProductClick.product_store_link_id == link_id))
    
    country_stats = db.session.execute(
        select(ProductClick.country, func.count(ProductClick.id))
        .where(ProductClick.product_store_link_id == link_id)
        .group_by(ProductClick.country)
        .order_by(func.count(ProductClick.id).desc())
        .limit(5)
    ).all()
    
    referrer_stats = db.session.execute(
        select(ProductClick.referrer, func.count(ProductClick.id))
        .where(ProductClick.product_store_link_id == link_id)
        .where(ProductClick.referrer.isnot(None))
        .where(ProductClick.referrer != "")
        .group_by(ProductClick.referrer)
        .order_by(func.count(ProductClick.id).desc())
        .limit(5)
    ).all()

    return {
        "link_data": link_data,
        "total_clicks": total_clicks,
        "latest_click": latest_click,
        "country_stats": country_stats,
        "referrer_stats": referrer_stats
    }
