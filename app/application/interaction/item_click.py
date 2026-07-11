from datetime import datetime, timedelta, timezone
from app.core.extensions import db
from app.domains.product.models import ProductStoreLink
from app.domains.interaction.models import ProductClick
from app.domains.recommendation.interest_service import handle_interaction_interest
from sqlalchemy import select

def record_item_click_workflow(link_id, user, ip_address, user_agent, referrer, country):
    """
    Handles product click tracking and interest updating.
    """
    link = db.session.get(ProductStoreLink, link_id)
    if not link:
        return None

    user_id = user.id if user and user.is_authenticated else None
    
    # Deduplicate click (24h)
    last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    stmt = select(ProductClick).where(
        ProductClick.product_store_link_id == link.id,
        ProductClick.created_at >= last_24h,
        (ProductClick.user_id == user_id if user_id else ProductClick.ip_address == ip_address)
    )
    existing = db.session.execute(stmt).scalars().first()

    if not existing:
        click = ProductClick(
            product_store_link_id=link.id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
            country=country
        )
        db.session.add(click)
        link.product.click_count = (link.product.click_count or 0) + 1
        db.session.commit()

    if user and user.is_authenticated:
        handle_interaction_interest(user=user, target=link.product, action="item_click", session=db.session)

    return link.affiliate_url
