def set_default_variant(product, variant):
    for v in product.variants:
        v.is_default = False
    variant.is_default = True

def ensure_default_variant(product):
    from app.domains.product.models import ProductVariant
    if not product.variants:
        variant = ProductVariant(product=product, title='Default', is_default=True, attributes={})
        product.variants.append(variant)
        return variant
    if not any((v.is_default for v in product.variants)):
        product.variants[0].is_default = True

def get_active_store_links(product):
    return [link for variant in product.variants for link in variant.store_links if link.is_active]