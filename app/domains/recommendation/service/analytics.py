from sqlalchemy import func, distinct, and_, select
from datetime import datetime, timedelta
from app.shared.constants.core import TargetType
from app.core.extensions import db
from app.domains.product.models import Product, ProductVariant, ProductStoreLink
from app.domains.interaction.models import ProductClick, View
def get_item_analytics(product_id, session=None):
    session = session or db.session
    last_24h = datetime.utcnow() - timedelta(hours=24)
    stmt_views_24h = select(func.count(distinct(func.coalesce(View.user_id, View.ip_address)))).where(View.target_type == TargetType.PRODUCT, View.target_id == product_id, View.created_at >= last_24h)
    views_24h = session.execute(stmt_views_24h).scalar() or 0
    stmt_views_all = select(func.count(distinct(func.coalesce(View.user_id, View.ip_address)))).where(View.target_type == TargetType.PRODUCT, View.target_id == product_id)
    views_all = session.execute(stmt_views_all).scalar() or 0
    stmt_clicks_24h = select(func.count(distinct(func.coalesce(ProductClick.user_id, ProductClick.ip_address)))).join(ProductStoreLink).join(ProductVariant).where(ProductVariant.product_id == product_id, ProductClick.created_at >= last_24h)
    clicks_24h = session.execute(stmt_clicks_24h).scalar() or 0
    stmt_clicks_all = select(func.count(distinct(func.coalesce(ProductClick.user_id, ProductClick.ip_address)))).join(ProductStoreLink).join(ProductVariant).where(ProductVariant.product_id == product_id)
    clicks_all = session.execute(stmt_clicks_all).scalar() or 0
    ctr_24h = clicks_24h / views_24h if views_24h else 0
    ctr_all = clicks_all / views_all if views_all else 0
    return {'views_24h': views_24h, 'views_all': views_all, 'clicks_24h': clicks_24h, 'clicks_all': clicks_all, 'ctr_24h': round(ctr_24h, 4), 'ctr_all': round(ctr_all, 4)}
def get_top_store_for_item(product_id, last_hours=24, session=None):
    session = session or db.session
    since = datetime.utcnow() - timedelta(hours=last_hours)
    stmt = select(ProductStoreLink.id, ProductStoreLink.store_id, func.count(ProductClick.id).label('clicks')).join(ProductClick).where(ProductStoreLink.variant_id == product_id, ProductClick.created_at >= since).group_by(ProductStoreLink.id).order_by(func.count(ProductClick.id).desc())
    row = session.execute(stmt).first()
    return row