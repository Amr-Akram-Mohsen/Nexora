from app.utils.request import get_country
from app.models import Item, ItemVariant, Store

def filter_items_by_country(query):
    country = get_country()
    if not country: return

    return query.join(Item.store_links)\
        .join(Store).filter(Store.country == country.upper())

def get_search_items(query):
    p_query = Item.query.filter(Item.name.ilike(f'%{query}%'))

    p_query = filter_items_by_country(p_query)

    return p_query.order_by(Item.created_at.desc()).limit(50).all()


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
