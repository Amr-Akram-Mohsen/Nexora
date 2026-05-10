from flask_sqlalchemy import pagination
from app.core.extensions import db
from ..models import Item, ItemVariant, Store, ItemStoreLink
from ...system.models import Category, Brand
from app.shared.parsing import safe_float
from app.infrastructure import cache

def serialize_item(item):
    default_variant = item.default_variant

    return {
        # ── Core identity ─────────────────────────────
        "id": item.id,
        "name": item.name,
        "slug": item.slug,
        "type": item.item_type,
        "card_type": item.card_type,

        # ── Relations (flattened) ─────────────────────
        "brand": {
            "name": item.brand.name,
            "slug": item.brand.slug
        } if item.brand else None,

        "category": {
            "name": item.category.name,
            "slug": item.category.slug
        } if item.category else None,

        # ── Media ─────────────────────────────────────
        "image": item.image_url,

        # ── Pricing ───────────────────────────────────
        "price": float(item.price) if item.price is not None else None,
        "min_price": float(item.min_price) if item.min_price is not None else None,
        "has_variants": item.has_variants,

        # ── Variant snapshot (important for UI) ───────
        "default_variant": {
            "id": default_variant.id,
            "sku": getattr(default_variant, "sku", None),
            "price": float(default_variant.price) if default_variant.price else None,
        } if default_variant else None,

        # ── Store availability (lightweight) ──────────
        "stores": [
            {
                "name": link.store.name,
                "slug": link.store.slug,
                "price": float(link.price),
                "currency": link.currency,
            }
            for link in item.store_links
        ] if item.store_links else [],

        # ── Stats ─────────────────────────────────────
        "rating": item.rating,
        "review_count": item.review_count,
        "view_count": item.view_count,

        # ── Metadata ──────────────────────────────────
        "created_at": item.created_at.isoformat() if item.created_at else None,

        # ── Optional lightweight attributes ───────────
        "badges": item.pick_keys(item.searchable_attributes, ["badge", "tag"]) if item.searchable_attributes else None,
    }

def filter_items_by_country(query):
    from app.shared.request import get_country
    country = get_country()
    if not country: return query

    return query.join(Item.variants).join(ItemVariant.store_links)\
        .join(Store).filter(Store.country == country.upper())

def get_search_items(query_str):
    p_query = Item.query.filter(Item.name.ilike(f'%{query_str}%'))
    return p_query.order_by(Item.created_at.desc()).limit(50).all()

@cache.memoize(timeout=300)
def get_filtered_items(active_filters, page=1, per_page=24):
    """
    Handles complex filtering, joining, and sorting for the items catalog.
    """
    query = Item.query.options(
        db.selectinload(Item.images),
        db.selectinload(Item.variants).selectinload(ItemVariant.store_links).selectinload(ItemStoreLink.store),
        db.joinedload(Item.brand),
        db.joinedload(Item.section),
        db.joinedload(Item.category),
    )

    # ── Category & Brand Filters ──────────────────────────────────
    if active_filters.get('category'):
        query = query.join(Item.category).filter(Category.slug.in_(active_filters['category']))
    if active_filters.get('brand'):
        query = query.join(Item.brand).filter(Brand.slug.in_(active_filters['brand']))
    if active_filters.get('type'):
        query = query.filter(Item.item_type.in_(active_filters['type']))
    
    # ── Store & Price Filters ─────────────────────────────────────
    has_store_filter = bool(active_filters.get('store'))
    min_p = safe_float(active_filters.get('min_price'))
    max_p = safe_float(active_filters.get('max_price'))
    has_price_filter = min_p is not None or max_p is not None
    
    sort_type = active_filters.get('sort', 'newest')
    needs_variant_join = has_store_filter or has_price_filter or sort_type in ['price_low', 'price_high']

    if needs_variant_join:
        query = query.join(Item.variants)
        if has_store_filter:
            query = query.join(ItemVariant.store_links).join(ItemStoreLink.store)\
                         .filter(Store.slug.in_(active_filters['store']))
        
        if min_p is not None:
            query = query.filter(ItemVariant.price >= min_p)
        if max_p is not None:
            query = query.filter(ItemVariant.price <= max_p)
            
        # Ensure we only pick default variants for price sorting/filtering to avoid duplicates
        if sort_type in ['price_low', 'price_high']:
            query = query.filter(ItemVariant.is_default == True)

    # ── Sorting ───────────────────────────────────────────────────
    if sort_type == 'price_low':
        query = query.order_by(ItemVariant.price.asc())
    elif sort_type == 'price_high':
        query = query.order_by(ItemVariant.price.desc())
    elif sort_type == 'popular':
        query = query.order_by(Item.view_count.desc())
    else:
        query = query.order_by(Item.created_at.desc())

    # query = query.distinct(Item.id)
    # return query.paginate(page=page, per_page=per_page, error_out=False)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        # ✅ 🔥 SERIALIZATION LAYER (THIS IS THE FIX)
    return {
        "items": [serialize_item(item) for item in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "prev_num": getattr(pagination, 'prev_num', pagination.page - 1 if pagination.has_prev else None),
        "next_num": getattr(pagination, 'next_num', pagination.page + 1 if pagination.has_next else None),
    }

def set_default_variant(item, variant):
    for v in item.variants:
        v.is_default = False
    variant.is_default = True

def ensure_default_variant(item):
    if not item.variants:
        variant = ItemVariant(
            item=item,
            title="Default",
            is_default=True,
            attributes={}
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


from app.domains.item.models import Item

def count_items():
    return db.session.query(Item.id).count()


def get_items(search=None, brand=None, rows_count=10):
    query = Item.query.order_by(Item.created_at.desc())

    if search and search.strip():
        from sqlalchemy import or_
        query = query.filter(or_(Item.name.ilike(f'%{search}%'), Item.description.ilike(f'%{search}%')))

    if brand:
        from app.domains.system.models import Brand
        query = query.join(Item.brand).filter(Brand.slug == brand)

    if rows_count:
        query = query.limit(rows_count)

    return query.all()
def get_distinct_stores():
    from ..models import Store, ItemStoreLink, ItemVariant, Item
    return Store.query.join(ItemStoreLink).join(ItemVariant).join(Item).distinct().all()

def get_distinct_item_types():
    from ..models import Item
    return [t[0] for t in db.session.query(Item.item_type).distinct().all() if t[0]]

def get_item_by_id(item_id):
    from ..models import Item, ItemVariant, ItemStoreLink
    return Item.query.options(
        db.selectinload(Item.variants)
            .selectinload(ItemVariant.store_links)
            .selectinload(ItemStoreLink.store),
        db.selectinload(Item.images)
    ).get(item_id)

def get_items_by_ids(item_ids):
    from ..models import Item, ItemVariant, ItemStoreLink
    return Item.query.options(
        db.joinedload(Item.brand),
        db.joinedload(Item.category),
        db.selectinload(Item.images),
        db.selectinload(Item.specifications),
        db.selectinload(Item.variants).selectinload(ItemVariant.store_links).selectinload(ItemStoreLink.store)
    ).filter(Item.id.in_(item_ids)).all()

@cache.memoize(timeout=600)
def get_filtered_items_for_home(filter_type='recent', limit=10):
    from ..models import ItemVariant
    query = Item.query.options(
        db.joinedload(Item.brand),
        db.joinedload(Item.category),
        db.selectinload(Item.images),
        db.selectinload(Item.variants).selectinload(ItemVariant.store_links)
    )

    if filter_type == 'deals':
        top_deals = query.join(Item.variants).filter(ItemVariant.old_price > ItemVariant.price).limit(limit).all()
        if not top_deals:
            top_deals = query.order_by(Item.id.desc()).limit(limit).all()
        return top_deals
    elif filter_type == 'random':
        return query.order_by(db.func.random()).limit(limit).all()
    else:
        return query.order_by(Item.created_at.desc()).limit(limit).all()
