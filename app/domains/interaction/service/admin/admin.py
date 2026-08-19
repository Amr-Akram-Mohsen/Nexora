from sqlalchemy import select, func, or_, case
from app.core.extensions import db
from app.domains.interaction.models import Comment, Reaction, View, Save, Share, ProductClick
from app.domains.user.models import User
from app.domains.content.models import Content
from app.domains.product.models import Product, ProductStoreLink, ProductVariant, Store
from app.domains.interaction.service.admin.serializers import serialize_comment, serialize_reaction, serialize_save, serialize_share
import math
from datetime import date, datetime
from app.shared.utils.orm_helpers import resolve_polymorphic_titles, resolve_users

def _load_interaction_context(products):
    users = resolve_users(products)
    titles_map = resolve_polymorphic_titles(products)
    return (users, titles_map)

def _load_target_titles(products, type_attr='target_type', id_attr='target_id'):
    return resolve_polymorphic_titles(products, type_attr, id_attr)

def get_admin_comments_page(page, per_page, sentiment, target_type, search, user_search, start_date, end_date):
    stmt = select(Comment).order_by(Comment.id.desc())
    if user_search:
        stmt = stmt.join(User, Comment.user_id == User.id)
    if sentiment:
        stmt = stmt.where(Comment.sentiment == sentiment)
    if target_type:
        stmt = stmt.where(Comment.target_type == target_type)
    if search:
        stmt = stmt.where(Comment.content.ilike(f'%{search}%'))
    if user_search:
        stmt = stmt.where(or_(User.name.ilike(f'%{user_search}%'), User.email.ilike(f'%{user_search}%')))
    if start_date:
        try:
            stmt = stmt.where(Comment.created_at >= datetime.combine(date.fromisoformat(start_date), datetime.min.time()))
        except ValueError:
            pass
    if end_date:
        try:
            stmt = stmt.where(Comment.created_at <= datetime.combine(date.fromisoformat(end_date), datetime.max.time()))
        except ValueError:
            pass
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    users, titles_map = _load_interaction_context(pagination.items)
    serialized = [serialize_comment(c, users, titles_map) for c in pagination.items]
    return (pagination, serialized)

def delete_admin_comment(id):
    comment = db.session.get(Comment, id)
    if not comment:
        return False
    db.session.delete(comment)
    db.session.commit()
    return True

def flag_admin_comment_as_spam(id):
    comment = db.session.get(Comment, id)
    if not comment:
        return False
    comment.sentiment = 'spam'
    db.session.commit()
    return True

def get_admin_reactions_page(page, per_page, reaction_type, target, user_search):
    stmt = select(Reaction).order_by(Reaction.id.desc())
    if reaction_type:
        stmt = stmt.where(Reaction.type == reaction_type)
    stmt = stmt.outerjoin(Content, (Reaction.target_id == Content.id) & (Reaction.target_type == 'content'))
    stmt = stmt.outerjoin(Product, (Reaction.target_id == Product.id) & (Reaction.target_type == 'product'))
    stmt = stmt.join(User, Reaction.user_id == User.id)
    if target:
        stmt = stmt.where(or_(Content.title.ilike(f'%{target}%'), Product.name.ilike(f'%{target}%')))
    if user_search:
        stmt = stmt.where(or_(User.name.ilike(f'%{user_search}%'), User.email.ilike(f'%{user_search}%')))
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    users, titles_map = _load_interaction_context(pagination.items)
    serialized = [serialize_reaction(r, users, titles_map) for r in pagination.items]
    return (pagination, serialized)

def get_admin_views_page(page, per_page, target, start_date, end_date):
    stmt = select(View.target_type, View.target_id, func.count(View.id).label('view_count'), func.sum(case((View.user_id.isnot(None), 1), else_=0)).label('auth_views'), func.sum(case((View.user_id.is_(None), 1), else_=0)).label('anon_views'), func.max(View.created_at).label('latest_view')).select_from(View)
    stmt = stmt.outerjoin(Content, (View.target_id == Content.id) & (View.target_type == 'content'))
    stmt = stmt.outerjoin(Product, (View.target_id == Product.id) & (View.target_type == 'product'))
    if target:
        stmt = stmt.where(or_(Content.title.ilike(f'%{target}%'), Product.name.ilike(f'%{target}%')))
    if start_date:
        try:
            stmt = stmt.where(View.created_at >= datetime.combine(date.fromisoformat(start_date), datetime.min.time()))
        except ValueError:
            pass
    if end_date:
        try:
            stmt = stmt.where(View.created_at <= datetime.combine(date.fromisoformat(end_date), datetime.max.time()))
        except ValueError:
            pass
    stmt = stmt.group_by(View.target_type, View.target_id).order_by(func.max(View.created_at).desc())
    total = db.session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    paginated_stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    products = db.session.execute(paginated_stmt).all()
    titles_map = _load_target_titles(products)
    result_items = []
    for row in products:
        row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
        row_dict['target_title'] = titles_map.get((row_dict['target_type'], row_dict['target_id']))
        result_items.append(row_dict)
    pages = math.ceil(total / per_page) if per_page > 0 else 1
    return {'products': result_items, 'page': page, 'pages': pages, 'total': total, 'per_page': per_page}

def get_admin_clicks_page(page, per_page, target, destination):
    stmt = select(ProductStoreLink.id.label('link_id'), ProductStoreLink.affiliate_url, Store.name.label('store_name'), Product.id.label('product_id'), Product.name.label('item_name'), func.count(ProductClick.id).label('click_count'), func.max(ProductClick.created_at).label('latest_click')).select_from(ProductClick).join(ProductStoreLink, ProductClick.product_store_link_id == ProductStoreLink.id).join(Store, ProductStoreLink.store_id == Store.id).join(ProductVariant, ProductStoreLink.variant_id == ProductVariant.id).join(Product, ProductVariant.product_id == Product.id)
    if target:
        stmt = stmt.where(or_(Product.name.ilike(f'%{target}%'), Store.name.ilike(f'%{target}%')))
    if destination:
        if destination.isdigit():
            stmt = stmt.where(Store.id == int(destination))
        else:
            stmt = stmt.where(Store.name.ilike(f'%{destination}%'))
    stmt = stmt.group_by(ProductStoreLink.id, ProductStoreLink.affiliate_url, Store.name, Product.id, Product.name).order_by(func.max(ProductClick.created_at).desc())
    total = db.session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    paginated_stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    products = db.session.execute(paginated_stmt).all()
    pages = math.ceil(total / per_page) if per_page > 0 else 1
    return {'products': products, 'page': page, 'pages': pages, 'total': total, 'per_page': per_page}

def get_admin_saves_page(page, per_page, target, user_search):
    stmt = select(Save).order_by(Save.id.desc())
    stmt = stmt.outerjoin(Content, (Save.target_id == Content.id) & (Save.target_type == 'content'))
    stmt = stmt.outerjoin(Product, (Save.target_id == Product.id) & (Save.target_type == 'product'))
    stmt = stmt.join(User, Save.user_id == User.id)
    if target:
        stmt = stmt.where(or_(Content.title.ilike(f'%{target}%'), Product.name.ilike(f'%{target}%')))
    if user_search:
        stmt = stmt.where(or_(User.name.ilike(f'%{user_search}%'), User.email.ilike(f'%{user_search}%')))
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    users, titles_map = _load_interaction_context(pagination.items)
    serialized = [serialize_save(s, users, titles_map) for s in pagination.items]
    return (pagination, serialized)

def get_admin_shares_page(page, per_page, target, user_search):
    stmt = select(Share).order_by(Share.id.desc())
    stmt = stmt.outerjoin(Content, (Share.target_id == Content.id) & (Share.target_type == 'content'))
    stmt = stmt.outerjoin(Product, (Share.target_id == Product.id) & (Share.target_type == 'product'))
    stmt = stmt.join(User, Share.user_id == User.id)
    if target:
        stmt = stmt.where(or_(Content.title.ilike(f'%{target}%'), Product.name.ilike(f'%{target}%')))
    if user_search:
        stmt = stmt.where(or_(User.name.ilike(f'%{user_search}%'), User.email.ilike(f'%{user_search}%')))
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    users, titles_map = _load_interaction_context(pagination.items)
    serialized = [serialize_share(s, users, titles_map) for s in pagination.items]
    return (pagination, serialized)