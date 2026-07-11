"""SQLAlchemy eager-load profiles for Product queries (mirrors content/service/query/options.py)."""

from functools import lru_cache

from app.core.extensions import db


@lru_cache(maxsize=1)
def _item_models():
    """Import Product graph after all domain models are registered."""
    from app.domains.product.models import Product, ProductVariant, ProductStoreLink

    return Product, ProductVariant, ProductStoreLink


def get_item_load_options(profile="detail"):
    if profile is None or profile == "none":
        return []
    if isinstance(profile, (list, tuple)):
        return list(profile)

    Product, ProductVariant, ProductStoreLink = _item_models()

    minimal = [
        db.joinedload(Product.brand),
        db.joinedload(Product.category),
    ]
    card = [
        *minimal,
        db.selectinload(Product.images),
        db.selectinload(Product.variants)
        .selectinload(ProductVariant.store_links)
        .selectinload(ProductStoreLink.store),
    ]
    detail = [
        *card,
        db.selectinload(Product.specifications),
        db.selectinload(Product.variants).selectinload(ProductVariant.images),
    ]
    profiles = {
        "minimal": minimal,
        "card": card,
        "detail": detail,
    }
    return list(profiles.get(profile, detail))


def get_item_card_load_options():
    return get_item_load_options("card")

