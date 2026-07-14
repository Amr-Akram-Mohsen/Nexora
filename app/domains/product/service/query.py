from sqlalchemy import or_, select

from app.core.extensions import db
from app.domains.product.models import Product, ProductVariant, Store, ProductStoreLink
from app.domains.taxonomy.models import Category, Brand
from app.shared.parsing import safe_float
from app.infrastructure import cache

from .options import get_item_load_options, get_item_card_load_options
from app.domains.product.serializers import serialize_item, serialize_item_detail


def filter_items_by_country(query):
    from app.shared.request import get_country

    country = get_country()
    if not country:
        return query

    return (
        query.join(Product.variants)
        .join(ProductVariant.store_links)
        .join(Store)
        .where(Store.country == country.upper())
    )


def _apply_catalog_sort(stmt, sort_type):
    if sort_type == "price_low":
        order = ProductVariant.price.asc()
    elif sort_type == "price_high":
        order = ProductVariant.price.desc()
    elif sort_type == "popular":
        return stmt.order_by(Product.view_count.desc(), Product.id.desc())
    else:
        return stmt.order_by(Product.created_at.desc(), Product.id.desc())

    return stmt.order_by(order, Product.id.desc())


@cache.memoize(timeout=300)
def get_filtered_items(active_filters, page=1, per_page=24):
    """
    Handles complex filtering, joining, and sorting for the products catalog.
    """
    from .utils import build_item_stmt
    from sqlalchemy import and_
    
    stmt = build_item_stmt(eager_load="card")

    if active_filters.get("category"):
        stmt = stmt.join(Product.category).where(
            Category.slug.in_(active_filters["category"])
        )
    if active_filters.get("brand"):
        stmt = stmt.join(Product.brand).where(Brand.slug.in_(active_filters["brand"]))
    if active_filters.get("type"):
        stmt = stmt.where(Product.product_type.in_(active_filters["type"]))

    has_store_filter = bool(active_filters.get("store"))
    min_p = safe_float(active_filters.get("min_price"))
    max_p = safe_float(active_filters.get("max_price"))
    has_price_filter = min_p is not None or max_p is not None
    sort_type = active_filters.get("sort", "newest")
    is_price_sort = sort_type in ["price_low", "price_high"]

    if has_store_filter or has_price_filter or is_price_sort:
        if is_price_sort:
            stmt = stmt.join(ProductVariant, and_(ProductVariant.product_id == Product.id, ProductVariant.is_default == True))
            if has_store_filter:
                stmt = stmt.where(ProductVariant.store_links.any(
                    ProductStoreLink.store.has(Store.slug.in_(active_filters["store"]))
                ))
            if min_p is not None:
                stmt = stmt.where(ProductVariant.price >= min_p)
            if max_p is not None:
                stmt = stmt.where(ProductVariant.price <= max_p)
        else:
            variant_conds = []
            if has_store_filter:
                variant_conds.append(ProductVariant.store_links.any(
                    ProductStoreLink.store.has(Store.slug.in_(active_filters["store"]))
                ))
            if min_p is not None:
                variant_conds.append(ProductVariant.price >= min_p)
            if max_p is not None:
                variant_conds.append(ProductVariant.price <= max_p)
                
            if variant_conds:
                stmt = stmt.where(Product.variants.any(and_(*variant_conds)))

    stmt = _apply_catalog_sort(stmt, sort_type)

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    return {
        "products": [serialize_item(product) for product in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "prev_num": getattr(
            pagination, "prev_num", pagination.page - 1 if pagination.has_prev else None
        ),
        "next_num": getattr(
            pagination, "next_num", pagination.page + 1 if pagination.has_next else None
        ),
    }

def set_default_variant(product, variant):
    for v in product.variants:
        v.is_default = False
    variant.is_default = True


def ensure_default_variant(product):
    if not product.variants:
        variant = ProductVariant(
            product=product, title="Default", is_default=True, attributes={}
        )
        product.variants.append(variant)
        return variant

    if not any(v.is_default for v in product.variants):
        product.variants[0].is_default = True


def get_active_store_links(product):
    return [
        link
        for variant in product.variants
        for link in variant.store_links
        if link.is_active
    ]


def count_items(session=None):
    from sqlalchemy import func
    if session is None:
        session = db.session
    return session.execute(select(func.count(Product.id))).scalar() or 0


def get_items(search=None, brand=None, rows_count=10, session=None):
    from .utils import build_item_stmt, fetch_items
    
    stmt = build_item_stmt(eager_load="card")
    stmt = stmt.order_by(Product.created_at.desc())

    if search and search.strip():
        stmt = stmt.where(
            or_(Product.name.ilike(f"%{search}%"), Product.description.ilike(f"%{search}%"))
        )

    if brand:
        stmt = stmt.join(Product.brand).where(Brand.slug == brand)

    if rows_count:
        stmt = stmt.limit(rows_count)

    return fetch_items(stmt, session)


@cache.memoize(timeout=3600)
def get_distinct_stores(session=None):
    from ..models import Store

    if session is None:
        session = db.session

    stmt = (
        select(Store.slug, Store.name)
        .join(ProductStoreLink)
        .join(ProductVariant)
        .join(Product)
        .distinct()
        .order_by(Store.name)
    )
    rows = session.execute(stmt).mappings().all()
    return [dict(row) for row in rows]


@cache.memoize(timeout=3600)
def get_distinct_product_types(session=None):
    if session is None:
        session = db.session
    stmt = select(Product.product_type).distinct().order_by(Product.product_type)
    rows = session.execute(stmt).scalars().all()
    return [t for t in rows if t]


def get_item_by_id(product_id, serialize=False, load="detail", session=None):
    from .utils import build_item_stmt, fetch_item
    
    stmt = build_item_stmt(eager_load=load).where(Product.id == product_id)
    product = fetch_item(stmt, session)
    if not product:
        return None

    if serialize:
        return serialize_item_detail(product) if load == "detail" else serialize_item(product)
    return product


def get_items_by_ids(product_ids, serialize=False, load="detail", session=None):
    from .utils import build_item_stmt, fetch_items
    
    if not product_ids:
        return []

    stmt = build_item_stmt(eager_load=load).where(Product.id.in_(product_ids))
    products = fetch_items(stmt, session)

    if serialize:
        fn = serialize_item_detail if load == "detail" else serialize_item
        return [fn(product) for product in products]
    return products

def get_related_items(product, limit=8, session=None):
    """
    Get related products from same category and optionally same brand.
    """
    from .utils import build_item_stmt, fetch_items
    
    if not product:
        return []

    stmt = build_item_stmt(eager_load="card").where(
        Product.id != product.id,
        Product.category_id == product.category_id
    )

    if product.brand_id:
        stmt = stmt.order_by(
            db.case(
                (Product.brand_id == product.brand_id, 0),
                else_=1
            ),
            Product.created_at.desc()
        )
    else:
        stmt = stmt.order_by(Product.created_at.desc())

    if limit:
        stmt = stmt.limit(limit)

    return fetch_items(stmt, session)

def get_item_spec_groups(product_id, session=None):
    """Lightweight spec payload for AJAX full-specs partial."""
    product = get_item_by_id(product_id, load="detail", session=session)
    if not product:
        return None
    structured = product.structured_details
    return structured.get("groups") if structured else None


@cache.memoize(timeout=600)
def get_filtered_items_for_home(filter_type="recent", limit=10, exclude_ids=None, session=None):
    from .utils import build_item_stmt, fetch_items
    
    stmt = build_item_stmt(eager_load="card")

    if exclude_ids:
        stmt = stmt.where(Product.id.notin_(list(exclude_ids)))

    if filter_type == "deals":
        stmt = (
            stmt.join(Product.variants)
            .where(ProductVariant.old_price > ProductVariant.price)
            .distinct(Product.id)
            .order_by(Product.id.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        products = fetch_items(stmt, session)
        if not products:
            stmt = build_item_stmt(eager_load="card").order_by(Product.created_at.desc())
            if exclude_ids:
                stmt = stmt.where(Product.id.notin_(list(exclude_ids)))
            if limit:
                stmt = stmt.limit(limit)
            products = fetch_items(stmt, session)
    elif filter_type == "random":
        stmt = stmt.order_by(db.func.random())
        if limit:
            stmt = stmt.limit(limit)
        products = fetch_items(stmt, session)
    else:
        stmt = stmt.order_by(Product.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        products = fetch_items(stmt, session)

    return [serialize_item(product) for product in products]

@cache.memoize(timeout=3600)
def get_distinct_stores(session=None):
    from ..models import Store

    if session is None:
        session = db.session

    stmt = (
        select(Store.slug, Store.name)
        .join(ProductStoreLink)
        .join(ProductVariant)
        .join(Product)
        .distinct()
        .order_by(Store.name)
    )
    rows = session.execute(stmt).mappings().all()
    return [dict(row) for row in rows]


@cache.memoize(timeout=3600)
def get_distinct_product_types(session=None):
    if session is None:
        session = db.session
    stmt = select(Product.product_type).distinct().order_by(Product.product_type)
    rows = session.execute(stmt).scalars().all()
    return [t for t in rows if t]


def get_item_by_id(product_id, serialize=False, load="detail", session=None):
    from .utils import build_item_stmt, fetch_item
    
    stmt = build_item_stmt(eager_load=load).where(Product.id == product_id)
    product = fetch_item(stmt, session)
    if not product:
        return None

    if serialize:
        return serialize_item_detail(product) if load == "detail" else serialize_item(product)
    return product


def get_items_by_ids(product_ids, serialize=False, load="detail", session=None):
    from .utils import build_item_stmt, fetch_items
    
    if not product_ids:
        return []

    stmt = build_item_stmt(eager_load=load).where(Product.id.in_(product_ids))
    products = fetch_items(stmt, session)

    if serialize:
        fn = serialize_item_detail if load == "detail" else serialize_item
        return [fn(product) for product in products]
    return products

def get_related_items(product, limit=8, session=None):
    """
    Get related products from same category and optionally same brand.
    """
    from .utils import build_item_stmt, fetch_items
    
    if not product:
        return []

    stmt = build_item_stmt(eager_load="card").where(
        Product.id != product.id,
        Product.category_id == product.category_id
    )

    if product.brand_id:
        stmt = stmt.order_by(
            db.case(
                (Product.brand_id == product.brand_id, 0),
                else_=1
            ),
            Product.created_at.desc()
        )
    else:
        stmt = stmt.order_by(Product.created_at.desc())

    if limit:
        stmt = stmt.limit(limit)

    return fetch_items(stmt, session)

def get_item_spec_groups(product_id, session=None):
    """Lightweight spec payload for AJAX full-specs partial."""
    product = get_item_by_id(product_id, load="detail", session=session)
    if not product:
        return None
    structured = product.structured_details
    return structured.get("groups") if structured else None


@cache.memoize(timeout=600)
def get_filtered_items_for_home(filter_type="recent", limit=10, exclude_ids=None, session=None):
    from .utils import build_item_stmt, fetch_items
    
    stmt = build_item_stmt(eager_load="card")

    if exclude_ids:
        stmt = stmt.where(Product.id.notin_(list(exclude_ids)))

    if filter_type == "deals":
        stmt = (
            stmt.join(Product.variants)
            .where(ProductVariant.old_price > ProductVariant.price)
            .distinct(Product.id)
            .order_by(Product.id.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        products = fetch_items(stmt, session)
        if not products:
            stmt = build_item_stmt(eager_load="card").order_by(Product.created_at.desc())
            if exclude_ids:
                stmt = stmt.where(Product.id.notin_(list(exclude_ids)))
            if limit:
                stmt = stmt.limit(limit)
            products = fetch_items(stmt, session)
    elif filter_type == "random":
        stmt = stmt.order_by(db.func.random())
        if limit:
            stmt = stmt.limit(limit)
        products = fetch_items(stmt, session)
    else:
        stmt = stmt.order_by(Product.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        products = fetch_items(stmt, session)

    return [serialize_item(product) for product in products]

def get_popular_items(
    category_slugs: tuple | None = None,
    brand_slugs: tuple | None = None,
    limit: int = 6,
    session=None
) -> list[dict]:
    from app.domains.product.models import Product
    from app.domains.taxonomy.models import Category, Brand
    from app.domains.product.service.utils import build_item_stmt, fetch_items
    from app.domains.product.serializers import serialize_item
    
    if session is None:
        from app.core.extensions import db
        session = db.session
    
    stmt = build_item_stmt(eager_load="card")
    if category_slugs:
        stmt = stmt.join(Product.category).where(Category.slug.in_(list(category_slugs)))
    if brand_slugs:
        stmt = stmt.join(Product.brand).where(Brand.slug.in_(list(brand_slugs)))
        
    stmt = stmt.order_by(Product.view_count.desc(), Product.created_at.desc())
    if limit:
        stmt = stmt.limit(limit)
        
    products = fetch_items(stmt, session)
    return [serialize_item(i) for i in products]

def get_all_items_metadata(session=None):
    from sqlalchemy import select
    from app.domains.product.models import Product
    if session is None:
        session = db.session
    stmt = select(Product.id, Product.created_at)
    return session.execute(stmt).all()


def get_candidate_items_for_content(content, session=None):
    from sqlalchemy import select, or_
    from app.domains.product.models import Product
    if session is None:
        from app.core.extensions import db
        session = db.session
    brand_slugs = [ce.entity.slug for ce in content.content_entities if ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand'] if content.content_entities else []
    brand_ids = []
    if brand_slugs:
        from app.domains.taxonomy.models import Brand
        brand_ids = [b.id for b in session.query(Brand.id).filter(Brand.slug.in_(brand_slugs)).all()]
        
    conditions = []
    if content.category_id:
        conditions.append(Product.category_id == content.category_id)
    if brand_ids:
        conditions.append(Product.brand_id.in_(brand_ids))
    if not conditions:
        return []
    stmt = select(Product).where(or_(*conditions))
    return session.execute(stmt).scalars().all()


def get_items_for_matching(cutoff=None, cutoff_naive=None, session=None):
    from sqlalchemy import select, or_
    from app.domains.product.models import Product
    if session is None:
        from app.core.extensions import db
        session = db.session
    stmt = select(Product)
    if cutoff and cutoff_naive:
        stmt = stmt.where(or_(Product.created_at >= cutoff, Product.created_at >= cutoff_naive))
    return session.execute(stmt).scalars().all()


def get_existing_content_product_links_by_items(product_ids, session=None):
    from sqlalchemy import select
    from app.domains.relationships import content_products
    if session is None:
        from app.core.extensions import db
        session = db.session
    stmt = select(content_products.c.content_id, content_products.c.product_id).where(content_products.c.product_id.in_(product_ids))
    return session.execute(stmt).all()
