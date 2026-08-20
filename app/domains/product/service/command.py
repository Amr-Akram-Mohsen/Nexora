from app.core.extensions import db
from app.domains.product.models import Product, ProductVariant


def delete_item(id: int) -> bool:
    product = db.session.get(Product, id)
    if not product:
        return False
    db.session.delete(product)
    return True


def set_default_variant(product: Product, variant: ProductVariant):
    for v in product.variants:
        v.is_default = False
    variant.is_default = True


def ensure_default_variant(product: Product) -> ProductVariant:
    if not product.variants:
        variant = ProductVariant(product=product, title='Default', is_default=True, attributes={})
        product.variants.append(variant)
        return variant
    if not any((v.is_default for v in product.variants)):
        product.variants[0].is_default = True
    return product.variants[0]


def get_active_store_links(product: Product):
    return [link for variant in product.variants for link in variant.store_links if link.is_active]