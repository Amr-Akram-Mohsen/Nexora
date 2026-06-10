"""SQLAlchemy eager-load profiles for Item queries (mirrors content/service/query/options.py)."""

from functools import lru_cache

from app.core.extensions import db


@lru_cache(maxsize=1)
def _item_models():
    """Import Item graph after all domain models are registered."""
    from app.domains.item.models import Item, ItemVariant, ItemStoreLink

    return Item, ItemVariant, ItemStoreLink


def get_item_load_options(profile="detail"):
    if profile is None or profile == "none":
        return []
    if isinstance(profile, (list, tuple)):
        return list(profile)

    Item, ItemVariant, ItemStoreLink = _item_models()

    minimal = [
        db.joinedload(Item.brand),
        db.joinedload(Item.category),
    ]
    card = [
        *minimal,
        db.selectinload(Item.images),
        db.selectinload(Item.variants)
        .selectinload(ItemVariant.store_links)
        .selectinload(ItemStoreLink.store),
    ]
    detail = [
        *card,
        db.selectinload(Item.specifications),
        db.selectinload(Item.variants).selectinload(ItemVariant.images),
    ]
    profiles = {
        "minimal": minimal,
        "card": card,
        "detail": detail,
    }
    return list(profiles.get(profile, detail))


def get_item_card_load_options():
    return get_item_load_options("card")

