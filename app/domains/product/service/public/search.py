from sqlalchemy import func, select, case as sa_case
from app.domains.product.models import Product
from app.domains.product.service import get_item_card_load_options


def build_item_search_vector(product):
    return (
        func.setweight(
            func.to_tsvector(
                "english",
                func.coalesce(
                    product.name,
                    ""
                )
            ),
            "A"
        ).op("||")(
            func.setweight(
                func.to_tsvector(
                    "english",
                    func.coalesce(
                        product.description,
                        ""
                    )
                ),
                "B"
            )
        ).op("||")(
            func.setweight(
                func.to_tsvector(
                    "english",
                    func.coalesce(
                        product.search_text,
                        ""
                    )
                ),
                "C"
            )
        )
    )


def populate_item_search_fields(product):

    brand_name = (
        product.brand.name
        if product.brand
        else ""
    )

    category_name = (
        product.category.name
        if product.category
        else ""
    )

    # Attribute facet names from the many-to-many relationship
    attribute_names = ""
    if hasattr(product, "attributes") and product.attributes:
        attribute_names = " ".join(
            attr.name for attr in product.attributes if attr.name
        )

    # Extract searchable_attributes JSON field (e.g. {"storage": "512GB", "RAM": "8GB"})
    # Both keys and values are included so queries like "512GB" or "8GB RAM" match.
    spec_text = ""
    if product.searchable_attributes and isinstance(product.searchable_attributes, dict):
        parts = []
        for k, v in product.searchable_attributes.items():
            if k:
                parts.append(str(k))
            if v:
                parts.append(str(v))
        spec_text = " ".join(parts)

    product.search_text = " ".join(
        filter(
            None,
            [
                product.name,
                product.description,

                brand_name,
                category_name,

                attribute_names,
                spec_text,

                product.product_type
            ]
        )
    )

    product.search_vector = build_item_search_vector(product)


def get_search_items(
    query_str,
    limit=80,
    session=None
):
    if session is None:
        from app.core.extensions import db
        session = db.session

    query_str = (query_str or "").strip()
    if not query_str:
        return []

    # websearch_to_tsquery handles operators (AND, OR, phrases, negation).
    # coalesce/nullif ensures we fall back to plainto_tsquery at the SQL level
    # when the web query would produce an empty tsquery (e.g. bare "-" input).
    web_q = func.websearch_to_tsquery("english", query_str)
    plain_q = func.plainto_tsquery("english", query_str)
    empty_q = func.to_tsquery("")
    search_query = func.coalesce(func.nullif(web_q, empty_q), plain_q)

    rank = func.ts_rank_cd(
        Product.search_vector,
        search_query
    )

    # Title prefix-match boost: products whose name starts with the raw query
    # string appear above purely ts_rank-ranked matches.
    title_boost = sa_case(
        (func.lower(Product.name).startswith(query_str.lower()), 0),
        else_=1
    )

    stmt = (
        select(Product)
        .options(*get_item_card_load_options())
        .where(
            Product.search_vector.op("@@")(search_query),
            Product.ingestion_status.in_(["published", "ready"])
        )
        .order_by(
            title_boost,
            rank.desc(),
            Product.review_count.desc(),
            Product.view_count.desc(),
            Product.created_at.desc()
        )
    )

    if limit:
        stmt = stmt.limit(limit)

    return session.execute(stmt).scalars().all()

def filter_items_by_country(query):
    from app.shared.request import get_country
    from app.domains.product.models import Product, ProductVariant, Store

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
    from app.domains.product.models import Product, ProductVariant
    if sort_type == "price_low":
        order = ProductVariant.price.asc()
    elif sort_type == "price_high":
        order = ProductVariant.price.desc()
    elif sort_type == "popular":
        return stmt.order_by(Product.view_count.desc(), Product.id.desc())
    else:
        return stmt.order_by(Product.created_at.desc(), Product.id.desc())

    return stmt.order_by(order, Product.id.desc())

from app.infrastructure.cache import cache
from app.core.extensions import db

@cache.memoize(timeout=300)
def get_filtered_items(active_filters, page=1, per_page=24):
    from app.domains.product.service.utils import build_item_stmt
    from sqlalchemy import and_
    from app.domains.product.models import Product, ProductVariant, Store, ProductStoreLink
    from app.domains.taxonomy.models import Category, Brand
    from app.shared.parsing import safe_float
    from app.domains.product.serializers import serialize_item
    
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


@cache.memoize(timeout=600)
def _get_home_products_cached(filter_type="recent", buffer_limit=10):
    from app.domains.product.service.utils import build_item_stmt, fetch_items
    from app.domains.product.models import Product, ProductVariant
    from app.domains.product.serializers import serialize_item
    
    stmt = build_item_stmt(eager_load="card")

    if filter_type == "deals":
        stmt = (
            stmt.join(Product.variants)
            .where(ProductVariant.old_price > ProductVariant.price)
            .distinct(Product.id)
            .order_by(Product.id.desc())
        )
        if buffer_limit:
            stmt = stmt.limit(buffer_limit)
        products = fetch_items(stmt, db.session)
        if not products:
            stmt = build_item_stmt(eager_load="card").order_by(Product.created_at.desc())
            if buffer_limit:
                stmt = stmt.limit(buffer_limit)
            products = fetch_items(stmt, db.session)
    elif filter_type == "random":
        stmt = stmt.order_by(db.func.random())
        if buffer_limit:
            stmt = stmt.limit(buffer_limit)
        products = fetch_items(stmt, db.session)
    else:
        stmt = stmt.order_by(Product.created_at.desc())
        if buffer_limit:
            stmt = stmt.limit(buffer_limit)
        products = fetch_items(stmt, db.session)

    return [serialize_item(product) for product in products]


def get_filtered_products_for_home(filter_type="recent", limit=10, exclude_ids=None):
    exclude_ids = exclude_ids or []
    buffer_limit = limit + len(exclude_ids)
    
    all_products = _get_home_products_cached(filter_type, buffer_limit)
    
    filtered = [p for p in all_products if p["id"] not in exclude_ids]
    return filtered[:limit]


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
