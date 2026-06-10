from sqlalchemy import or_, select

from app.core.extensions import db
from app.domains.item.models import Item, ItemVariant, Store, ItemStoreLink
from app.domains.taxonomy.models import Category, Brand, Topic
from app.shared.parsing import safe_float
from app.infrastructure import cache

from .options import get_item_load_options, get_item_card_load_options
from .serializers import serialize_item, serialize_item_detail


def filter_items_by_country(query):
    from app.shared.request import get_country

    country = get_country()
    if not country:
        return query

    return (
        query.join(Item.variants)
        .join(ItemVariant.store_links)
        .join(Store)
        .where(Store.country == country.upper())
    )


def _apply_catalog_sort(stmt, sort_type, needs_variant_join):
    if sort_type == "price_low":
        order = ItemVariant.price.asc()
    elif sort_type == "price_high":
        order = ItemVariant.price.desc()
    elif sort_type == "popular":
        return stmt.order_by(Item.view_count.desc(), Item.id.desc())
    else:
        return stmt.order_by(Item.created_at.desc(), Item.id.desc())

    if needs_variant_join:
        return stmt.order_by(order, Item.id.desc())
    return stmt.order_by(order)


@cache.memoize(timeout=300)
def get_filtered_items(active_filters, page=1, per_page=24):
    """
    Handles complex filtering, joining, and sorting for the items catalog.
    """
    from .utils import build_item_stmt
    
    stmt = build_item_stmt(eager_load="card")

    if active_filters.get("category"):
        stmt = stmt.join(Item.category).where(
            Category.slug.in_(active_filters["category"])
        )
    if active_filters.get("brand"):
        stmt = stmt.join(Item.brand).where(Brand.slug.in_(active_filters["brand"]))
    if active_filters.get("type"):
        stmt = stmt.where(Item.item_type.in_(active_filters["type"]))

    has_store_filter = bool(active_filters.get("store"))
    min_p = safe_float(active_filters.get("min_price"))
    max_p = safe_float(active_filters.get("max_price"))
    has_price_filter = min_p is not None or max_p is not None

    sort_type = active_filters.get("sort", "newest")
    needs_variant_join = (
        has_store_filter or has_price_filter or sort_type in ["price_low", "price_high"]
    )

    if needs_variant_join:
        stmt = stmt.join(Item.variants)
        if has_store_filter:
            stmt = (
                stmt.join(ItemVariant.store_links)
                .join(ItemStoreLink.store)
                .where(Store.slug.in_(active_filters["store"]))
            )

        if min_p is not None:
            stmt = stmt.where(ItemVariant.price >= min_p)
        if max_p is not None:
            stmt = stmt.where(ItemVariant.price <= max_p)

        if sort_type in ["price_low", "price_high"]:
            stmt = stmt.where(ItemVariant.is_default.is_(True))

        stmt = stmt.distinct(Item.id)

    stmt = _apply_catalog_sort(stmt, sort_type, needs_variant_join)

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    return {
        "items": [serialize_item(item) for item in pagination.items],
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

def set_default_variant(item, variant):
    for v in item.variants:
        v.is_default = False
    variant.is_default = True


def ensure_default_variant(item):
    if not item.variants:
        variant = ItemVariant(
            item=item, title="Default", is_default=True, attributes={}
        )
        item.variants.append(variant)
        return variant

    if not any(v.is_default for v in item.variants):
        item.variants[0].is_default = True


def get_active_store_links(item):
    return [
        link
        for variant in item.variants
        for link in variant.store_links
        if link.is_active
    ]


def count_items(session=None):
    from sqlalchemy import func
    if session is None:
        session = db.session
    return session.execute(select(func.count(Item.id))).scalar() or 0


def get_items(search=None, brand=None, rows_count=10, session=None):
    from .utils import build_item_stmt, fetch_items
    
    stmt = build_item_stmt(eager_load="card")
    stmt = stmt.order_by(Item.created_at.desc())

    if search and search.strip():
        stmt = stmt.where(
            or_(Item.name.ilike(f"%{search}%"), Item.description.ilike(f"%{search}%"))
        )

    if brand:
        stmt = stmt.join(Item.brand).where(Brand.slug == brand)

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
        .join(ItemStoreLink)
        .join(ItemVariant)
        .join(Item)
        .distinct()
        .order_by(Store.name)
    )
    return session.execute(stmt).mappings().all()


@cache.memoize(timeout=3600)
def get_distinct_item_types(session=None):
    if session is None:
        session = db.session
    stmt = select(Item.item_type).distinct().order_by(Item.item_type)
    rows = session.execute(stmt).scalars().all()
    return [t for t in rows if t]


def get_item_by_id(item_id, serialize=False, load="detail", session=None):
    from .utils import build_item_stmt, fetch_item
    
    stmt = build_item_stmt(eager_load=load).where(Item.id == item_id)
    item = fetch_item(stmt, session)
    if not item:
        return None

    if serialize:
        return serialize_item_detail(item) if load == "detail" else serialize_item(item)
    return item


def get_items_by_ids(item_ids, serialize=False, load="detail", session=None):
    from .utils import build_item_stmt, fetch_items
    
    if not item_ids:
        return []

    stmt = build_item_stmt(eager_load=load).where(Item.id.in_(item_ids))
    items = fetch_items(stmt, session)

    if serialize:
        fn = serialize_item_detail if load == "detail" else serialize_item
        return [fn(item) for item in items]
    return items

def get_related_items(item, limit=8, session=None):
    """
    Get related items from same category and optionally same brand.
    """
    from .utils import build_item_stmt, fetch_items
    
    if not item:
        return []

    stmt = build_item_stmt(eager_load="card").where(
        Item.id != item.id,
        Item.category_id == item.category_id
    )

    if item.brand_id:
        stmt = stmt.order_by(
            db.case(
                (Item.brand_id == item.brand_id, 0),
                else_=1
            ),
            Item.created_at.desc()
        )
    else:
        stmt = stmt.order_by(Item.created_at.desc())

    if limit:
        stmt = stmt.limit(limit)

    return fetch_items(stmt, session)

def get_item_spec_groups(item_id):
    """Lightweight spec payload for AJAX full-specs partial."""
    item = get_item_by_id(item_id, load="detail")
    if not item:
        return None
    structured = item.structured_details
    return structured.get("groups") if structured else None


@cache.memoize(timeout=600)
def get_filtered_items_for_home(filter_type="recent", limit=10, session=None):
    from .utils import build_item_stmt, fetch_items
    
    stmt = build_item_stmt(eager_load="card")

    if filter_type == "deals":
        stmt = (
            stmt.join(Item.variants)
            .where(ItemVariant.old_price > ItemVariant.price)
            .order_by(Item.id.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        items = fetch_items(stmt, session)
        if not items:
            stmt = build_item_stmt(eager_load="card").order_by(Item.created_at.desc())
            if limit:
                stmt = stmt.limit(limit)
            items = fetch_items(stmt, session)
    elif filter_type == "random":
        stmt = stmt.order_by(db.func.random())
        if limit:
            stmt = stmt.limit(limit)
        items = fetch_items(stmt, session)
    else:
        stmt = stmt.order_by(Item.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        items = fetch_items(stmt, session)

    return [serialize_item(item) for item in items]

