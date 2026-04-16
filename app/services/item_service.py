from app.models import db, Item, ItemVariant, Store, Category, Brand, ItemStoreLink
from app.utils.parsing import safe_float

def filter_items_by_country(query):
    from app.utils.request import get_country
    country = get_country()
    if not country: return query

    return query.join(Item.variants).join(ItemVariant.store_links)\
        .join(Store).filter(Store.country == country.upper())

def get_search_items(query_str):
    p_query = Item.query.filter(Item.name.ilike(f'%{query_str}%'))
    return p_query.order_by(Item.created_at.desc()).limit(50).all()

def get_filtered_items(active_filters, page=1, per_page=24):
    """
    Handles complex filtering, joining, and sorting for the items catalog.
    """
    query = Item.query.options(
        db.joinedload(Item.brand),
        db.joinedload(Item.category),
        db.selectinload(Item.images),
        db.selectinload(Item.variants).selectinload(ItemVariant.store_links).selectinload(ItemStoreLink.store)
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

    return query.distinct().paginate(page=page, per_page=per_page, error_out=False)

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

