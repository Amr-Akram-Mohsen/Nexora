from sqlalchemy import or_, select

from app.core.extensions import db
from app.domains.item.models import Item, ItemVariant, Store, ItemStoreLink
from app.domains.system.models import Category, Brand, Topic
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
        .filter(Store.country == country.upper())
    )


def _apply_catalog_sort(query, sort_type, needs_variant_join):
    if sort_type == "price_low":
        order = ItemVariant.price.asc()
    elif sort_type == "price_high":
        order = ItemVariant.price.desc()
    elif sort_type == "popular":
        return query.order_by(Item.view_count.desc(), Item.id.desc())
    else:
        return query.order_by(Item.created_at.desc(), Item.id.desc())

    if needs_variant_join:
        return query.order_by(order, Item.id.desc())
    return query.order_by(order)


@cache.memoize(timeout=300)
def get_filtered_items(active_filters, page=1, per_page=24):
    """
    Handles complex filtering, joining, and sorting for the items catalog.
    """
    query = Item.query.options(*get_item_card_load_options())

    if active_filters.get("category"):
        query = query.join(Item.category).filter(
            Category.slug.in_(active_filters["category"])
        )
    if active_filters.get("brand"):
        query = query.join(Item.brand).filter(Brand.slug.in_(active_filters["brand"]))
    if active_filters.get("type"):
        query = query.filter(Item.item_type.in_(active_filters["type"]))

    has_store_filter = bool(active_filters.get("store"))
    min_p = safe_float(active_filters.get("min_price"))
    max_p = safe_float(active_filters.get("max_price"))
    has_price_filter = min_p is not None or max_p is not None

    sort_type = active_filters.get("sort", "newest")
    needs_variant_join = (
        has_store_filter or has_price_filter or sort_type in ["price_low", "price_high"]
    )

    if needs_variant_join:
        query = query.join(Item.variants)
        if has_store_filter:
            query = (
                query.join(ItemVariant.store_links)
                .join(ItemStoreLink.store)
                .filter(Store.slug.in_(active_filters["store"]))
            )

        if min_p is not None:
            query = query.filter(ItemVariant.price >= min_p)
        if max_p is not None:
            query = query.filter(ItemVariant.price <= max_p)

        if sort_type in ["price_low", "price_high"]:
            query = query.filter(ItemVariant.is_default.is_(True))

        query = query.distinct(Item.id)

    query = _apply_catalog_sort(query, sort_type, needs_variant_join)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
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


def count_items():
    return db.session.query(Item.id).count()


def get_items(search=None, brand=None, rows_count=10):
    query = Item.query.options(*get_item_card_load_options()).order_by(Item.created_at.desc())

    if search and search.strip():
        query = query.filter(
            or_(Item.name.ilike(f"%{search}%"), Item.description.ilike(f"%{search}%"))
        )

    if brand:
        query = query.join(Item.brand).filter(Brand.slug == brand)

    if rows_count:
        query = query.limit(rows_count)

    return query.all()


@cache.memoize(timeout=3600)
def get_distinct_stores():
    from ..models import Store

    stmt = (
        select(Store.slug, Store.name)
        .join(ItemStoreLink)
        .join(ItemVariant)
        .join(Item)
        .distinct()
        .order_by(Store.name)
    )
    return db.session.execute(stmt).mappings().all()


@cache.memoize(timeout=3600)
def get_distinct_item_types():
    rows = db.session.query(Item.item_type).distinct().order_by(Item.item_type).all()
    return [t[0] for t in rows if t[0]]


def get_item_by_id(item_id, serialize=False, load="detail"):
    item = (
        Item.query.options(*get_item_load_options(load)).filter_by(id=item_id).first()
    )
    if not item:
        return None

    if serialize:
        return serialize_item_detail(item) if load == "detail" else serialize_item(item)
    return item


def get_items_by_ids(item_ids, serialize=False, load="detail"):
    if not item_ids:
        return [] if serialize else []

    items = (
        Item.query.options(*get_item_load_options(load))
        .filter(Item.id.in_(item_ids))
        .all()
    )

    if serialize:
        fn = serialize_item_detail if load == "detail" else serialize_item
        return [fn(item) for item in items]
    return items

def get_related_items(item, limit=8):
    """
    Get related items from same category and optionally same brand.
    """

    query = (
        Item.query
        .options(*get_item_card_load_options())
        .filter(
            Item.id != item.id,
            Item.category_id == item.category_id
        )
    )

    if item.brand_id:
        query = query.order_by(
            db.case(
                (Item.brand_id == item.brand_id, 0),
                else_=1
            ),
            Item.created_at.desc()
        )

    return query.limit(limit).all()

def get_item_spec_groups(item_id):
    """Lightweight spec payload for AJAX full-specs partial."""
    item = get_item_by_id(item_id, load="detail")
    if not item:
        return None
    structured = item.structured_details
    return structured.get("groups") if structured else None


@cache.memoize(timeout=600)
def get_filtered_items_for_home(filter_type="recent", limit=10):
    base = Item.query.options(*get_item_card_load_options())

    if filter_type == "deals":
        items = (
            base.join(Item.variants)
            .filter(ItemVariant.old_price > ItemVariant.price)
            .distinct(Item.id)
            .order_by(Item.id.desc())
            .limit(limit)
            .all()
        )
        if not items:
            items = (
                Item.query.options(*get_item_card_load_options())
                .order_by(Item.created_at.desc())
                .limit(limit)
                .all()
            )
    elif filter_type == "random":
        items = base.order_by(db.func.random()).limit(limit).all()
    else:
        items = base.order_by(Item.created_at.desc()).limit(limit).all()

    return [serialize_item(item) for item in items]
