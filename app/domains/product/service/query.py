from sqlalchemy import or_, select
from app.core.extensions import db
from app.domains.product.models import Product, ProductVariant, Store, ProductStoreLink
from app.domains.taxonomy.models import Category, Brand
from app.shared.parsing import safe_float
from app.infrastructure import cache
from .options import get_item_load_options, get_item_card_load_options
from app.domains.product.serializers import serialize_item, serialize_item_detail

def count_items():
    from sqlalchemy import func
    return db.session.execute(select(func.count(Product.id))).scalar() or 0

def get_items(search=None, brand=None, rows_count=10):
    from .utils import build_item_stmt, fetch_items
    stmt = build_item_stmt(eager_load='card')
    stmt = stmt.order_by(Product.created_at.desc())
    if search and search.strip():
        stmt = stmt.where(or_(Product.name.ilike(f'%{search}%'), Product.description.ilike(f'%{search}%')))
    if brand:
        stmt = stmt.join(Product.brand).where(Brand.slug == brand)
    if rows_count:
        stmt = stmt.limit(rows_count)
    return fetch_items(stmt)

@cache.memoize(timeout=3600)
def get_distinct_stores():
    from ..models import Store
    stmt = select(Store.slug, Store.name).join(ProductStoreLink).join(ProductVariant).join(Product).distinct().order_by(Store.name)
    rows = db.session.execute(stmt).mappings().all()
    return [dict(row) for row in rows]

@cache.memoize(timeout=3600)
def get_distinct_product_types():
    stmt = select(Product.product_type).distinct().order_by(Product.product_type)
    rows = db.session.execute(stmt).scalars().all()
    return [t for t in rows if t]

def get_item_by_id(product_id, serialize=False, load='detail'):
    from .utils import build_item_stmt, fetch_item
    stmt = build_item_stmt(eager_load=load).where(Product.id == product_id)
    product = fetch_item(stmt)
    if not product:
        return None
    if serialize:
        return serialize_item_detail(product) if load == 'detail' else serialize_item(product)
    return product

def get_items_by_ids(product_ids, serialize=False, load='detail'):
    from .utils import build_item_stmt, fetch_items
    if not product_ids:
        return []
    stmt = build_item_stmt(eager_load=load).where(Product.id.in_(product_ids))
    products = fetch_items(stmt)
    if serialize:
        fn = serialize_item_detail if load == 'detail' else serialize_item
        return [fn(product) for product in products]
    return products

def get_related_items(product, limit=8):
    from .utils import build_item_stmt, fetch_items
    if not product:
        return []
    stmt = build_item_stmt(eager_load='card').where(Product.id != product.id, Product.category_id == product.category_id)
    if product.brand_id:
        stmt = stmt.order_by(db.case((Product.brand_id == product.brand_id, 0), else_=1), Product.created_at.desc())
    else:
        stmt = stmt.order_by(Product.created_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    return fetch_items(stmt)

def get_item_spec_groups(product_id):
    product = get_item_by_id(product_id, load='detail', session=db.session)
    if not product:
        return None
    structured = product.structured_details
    return structured.get('groups') if structured else None

@cache.memoize(timeout=3600)
def get_distinct_stores():
    from ..models import Store
    stmt = select(Store.slug, Store.name).join(ProductStoreLink).join(ProductVariant).join(Product).distinct().order_by(Store.name)
    rows = db.session.execute(stmt).mappings().all()
    return [dict(row) for row in rows]

@cache.memoize(timeout=3600)
def get_distinct_product_types():
    stmt = select(Product.product_type).distinct().order_by(Product.product_type)
    rows = db.session.execute(stmt).scalars().all()
    return [t for t in rows if t]

def get_item_by_id(product_id, serialize=False, load='detail'):
    from .utils import build_item_stmt, fetch_item
    stmt = build_item_stmt(eager_load=load).where(Product.id == product_id)
    product = fetch_item(stmt)
    if not product:
        return None
    if serialize:
        return serialize_item_detail(product) if load == 'detail' else serialize_item(product)
    return product

def get_items_by_ids(product_ids, serialize=False, load='detail'):
    from .utils import build_item_stmt, fetch_items
    if not product_ids:
        return []
    stmt = build_item_stmt(eager_load=load).where(Product.id.in_(product_ids))
    products = fetch_items(stmt)
    if serialize:
        fn = serialize_item_detail if load == 'detail' else serialize_item
        return [fn(product) for product in products]
    return products

def get_related_items(product, limit=8):
    from .utils import build_item_stmt, fetch_items
    if not product:
        return []
    stmt = build_item_stmt(eager_load='card').where(Product.id != product.id, Product.category_id == product.category_id)
    if product.brand_id:
        stmt = stmt.order_by(db.case((Product.brand_id == product.brand_id, 0), else_=1), Product.created_at.desc())
    else:
        stmt = stmt.order_by(Product.created_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    return fetch_items(stmt)

def get_item_spec_groups(product_id):
    product = get_item_by_id(product_id, load='detail', session=db.session)
    if not product:
        return None
    structured = product.structured_details
    return structured.get('groups') if structured else None

def get_all_items_metadata():
    from sqlalchemy import select
    from app.domains.product.models import Product
    stmt = select(Product.id, Product.created_at)
    return db.session.execute(stmt).all()

def get_candidate_items_for_content(content):
    from sqlalchemy import select, or_
    from app.domains.product.models import Product
    brand_slugs = [ce.entity.slug for ce in content.content_entities if ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand'] if content.content_entities else []
    brand_ids = []
    if brand_slugs:
        from app.domains.taxonomy.models import Brand
        brand_ids = [b.id for b in db.session.query(Brand.id).filter(Brand.slug.in_(brand_slugs)).all()]
    conditions = []
    if content.category_id:
        conditions.append(Product.category_id == content.category_id)
    if brand_ids:
        conditions.append(Product.brand_id.in_(brand_ids))
    if not conditions:
        return []
    stmt = select(Product).where(or_(*conditions))
    return db.session.execute(stmt).scalars().all()

def get_items_for_matching(cutoff=None, cutoff_naive=None):
    from sqlalchemy import select, or_
    from app.domains.product.models import Product
    stmt = select(Product)
    if cutoff and cutoff_naive:
        stmt = stmt.where(or_(Product.created_at >= cutoff, Product.created_at >= cutoff_naive))
    return db.session.execute(stmt).scalars().all()

def get_existing_content_product_links_by_items(product_ids):
    from sqlalchemy import select
    from app.domains.relationships import content_products
    stmt = select(content_products.c.content_id, content_products.c.product_id).where(content_products.c.product_id.in_(product_ids))
    return db.session.execute(stmt).all()