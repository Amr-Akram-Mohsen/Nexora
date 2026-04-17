from sqlalchemy import func, distinct, and_
from datetime import datetime, timedelta
from app.core.constants import TargetType
from app.core.extensions import db
from app.domains.item.models import Item, ItemVariant, ItemStoreLink
from app.domains.interaction.models import ItemClick, View

def get_item_analytics(item_id):
    last_24h = datetime.utcnow() - timedelta(hours=24)

    # ---- Views ----
    views_24h = db.session.query(
        func.count(distinct(
            func.coalesce(View.user_id, View.ip_address)
        ))
    ).filter(
        View.target_type == TargetType.ITEM,
        View.target_id == item_id,
        View.created_at >= last_24h
    ).scalar() or 0

    views_all = db.session.query(
        func.count(distinct(
            func.coalesce(View.user_id, View.ip_address)
        ))
    ).filter(
        View.target_type == TargetType.ITEM,
        View.target_id == item_id
    ).scalar() or 0

    # ---- Clicks ----
    clicks_24h = db.session.query(
        func.count(distinct(
            func.coalesce(ItemClick.user_id, ItemClick.ip_address)
        ))
    ).join(ItemStoreLink)\
    .join(ItemVariant)\
    .filter(
        ItemVariant.item_id == item_id,
        ItemClick.created_at >= last_24h
    ).scalar() or 0

    clicks_all = db.session.query(
        func.count(distinct(
            func.coalesce(ItemClick.user_id, ItemClick.ip_address)
        ))
    ).join(ItemStoreLink)\
    .join(ItemVariant)\
    .filter(
        ItemVariant.item_id == item_id
    ).scalar() or 0

    # ---- CTR ----
    ctr_24h = (clicks_24h / views_24h) if views_24h else 0
    ctr_all = (clicks_all / views_all) if views_all else 0

    return {
        "views_24h": views_24h,
        "views_all": views_all,
        "clicks_24h": clicks_24h,
        "clicks_all": clicks_all,
        "ctr_24h": round(ctr_24h, 4),
        "ctr_all": round(ctr_all, 4),
    }

def get_top_store_for_item(item_id, last_hours=24):
    since = datetime.utcnow() - timedelta(hours=last_hours)

    row = db.session.query(
        ItemStoreLink.id,
        ItemStoreLink.store_id,
        func.count(ItemClick.id).label("clicks")
    ).join(ItemClick).filter(
        ItemStoreLink.variant_id == item_id,
        ItemClick.created_at >= since
    ).group_by(ItemStoreLink.id).order_by(
        func.count(ItemClick.id).desc()
    ).first()

    return row  # None if no clicks
