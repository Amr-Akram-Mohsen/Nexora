from datetime import datetime, timedelta, timezone
from app.core.extensions import db
from app.domains.item.models import ItemStoreLink
from app.domains.interaction.models import ItemClick
from app.domains.recommendation.interest_service import handle_interaction_interest

def record_item_click_workflow(link_id, user, ip_address, user_agent, referrer, country):
    """
    Handles item click tracking and interest updating.
    """
    link = ItemStoreLink.query.get(link_id)
    if not link:
        return None

    user_id = user.id if user and user.is_authenticated else None
    
    # Deduplicate click (24h)
    last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    existing = ItemClick.query.filter(
        ItemClick.item_store_link_id == link.id,
        ItemClick.created_at >= last_24h,
        (ItemClick.user_id == user_id if user_id else ItemClick.ip_address == ip_address)
    ).first()

    if not existing:
        click = ItemClick(
            item_store_link_id=link.id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
            country=country
        )
        db.session.add(click)
        link.item.click_count = (link.item.click_count or 0) + 1
        db.session.commit()

    if user and user.is_authenticated:
        handle_interaction_interest(user=user, target=link.item, action="item_click")

    return link.affiliate_url
