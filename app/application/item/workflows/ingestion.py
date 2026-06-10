# app/scrapers/item_storer.py
"""
Stores items and store links from Amazon PA-API into the Item model.
Deduplicates based on ASIN+Country.
Automatically links items to Section, Category, and Brand.
"""
import logging
from slugify import slugify
from app.core.extensions import db
from app.domains.item.models import Item, ItemVariant, ItemImage, ItemStoreLink, Store, ItemSpecification
from app.domains.taxonomy.models import Brand, Category

logger = logging.getLogger(__name__)

DEFAULT_ITEM_TYPE = "electronics"


def get_or_create_brand(name: str) -> Brand:
    slug = slugify(name)
    brand = Brand.query.filter_by(slug=slug).first()
    if not brand:
        brand = Brand(name=name, slug=slug)
        db.session.add(brand)
        db.session.flush()
    return brand


def get_or_create_category(slug: str) -> Category:
    cat = Category.query.filter_by(slug=slug).first()
    if not cat:
        name = slug.replace("-", " ").title()
        cat = Category(name=name, slug=slug)
        db.session.add(cat)
        db.session.flush()
    return cat


def get_amazon_store(country: str) -> Store:
    """Check for or create an Amazon store record for SA or AE."""
    slug = f"amazon-{country.lower()}"
    store = Store.query.filter_by(slug=slug).first()
    if not store:
        store = Store(
            name=f"Amazon {country.upper()}",
            slug=slug,
            website=f"https://www.amazon.{'sa' if country.lower() == 'sa' else 'ae'}",
            country=country.upper(),
            currency="SAR" if country.lower() == 'sa' else "AED",
            affiliate_network="Amazon Associates",
            logo_url="https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()
    return store


def store_amazon_item(data: dict) -> Item | None:
    """
    Store an item from Amazon PA-API data.
    - Resolves/Creates Brand
    - Resolves/Creates Category (based on category_slug)
    - Adds Item + ItemVariant + StoreLink + Images
    """
    brand_name = data.get("brand_name") or "Unknown"
    brand = get_or_create_brand(brand_name)
    category_slug = data.get("category_slug") or "electronics"
    category = get_or_create_category(category_slug)
    store = get_amazon_store(data["country"])

    item_name = data["name"]
    slug = slugify(item_name)

    # ── Resolve or Create Item ────────────────────────────────────
    item = Item.query.filter_by(slug=slug, brand_id=brand.id).first()
    if not item:
        # Determine item type (heuristically for structured details schema)
        item_type = DEFAULT_ITEM_TYPE
        if "perfume" in category_slug or "fragrance" in category_slug:
            item_type = "perfumes"
        elif "accessories" in category_slug or "watch" in category_slug:
            item_type = "accessories"

        item = Item(
            name=item_name,
            slug=slug,
            brand_id=brand.id,
            category_id=category.id,
            item_type=item_type,
            description="\n".join(data.get("features", [])[:3]),
        )
        db.session.add(item)
        db.session.flush()

        # Add image
        if data.get("image_url"):
            db.session.add(ItemImage(item_id=item.id, image_url=data["image_url"], position=0))

        # Add default variant
        variant = ItemVariant(
            item_id=item.id, title="Default", is_default=True, attributes={},
            price=data.get("price"), old_price=data.get("old_price"), currency=data.get("currency")
        )
        db.session.add(variant)
        db.session.flush()

        # Store features as specification
        if data.get("features"):
            db.session.add(ItemSpecification(
                item_id=item.id,
                category="features",
                spec_json={"bullets": data["features"]}
            ))
    else:
        variant = item.default_variant
        if not variant:
            variant = ItemVariant(
                item_id=item.id, title="Default", is_default=True, attributes={},
                price=data.get("price"), old_price=data.get("old_price"), currency=data.get("currency")
            )
            db.session.add(variant)
            db.session.flush()
        else:
            # Update variant price if it's the default one being discovered
            if variant.is_default:
                variant.price = data.get("price", variant.price)
                variant.old_price = data.get("old_price", variant.old_price)
                variant.currency = data.get("currency", variant.currency)

    # ── Resolve or Create StoreLink ───────────────────────────────
    link = ItemStoreLink.query.filter_by(variant_id=variant.id, store_id=store.id).first()
    from datetime import datetime
    if link:
        link.price = data.get("price", link.price)
        link.old_price = data.get("old_price")
        link.availability = data.get("availability", link.availability)
        link.affiliate_url = data["affiliate_url"]
        link.last_checked_at = datetime.utcnow()
    else:
        link = ItemStoreLink(
            variant_id=variant.id,
            store_id=store.id,
            external_item_id=data["asin"], # ASIN used for re-fetching
            affiliate_url=data["affiliate_url"],
            price=data.get("price"),
            old_price=data.get("old_price"),
            currency=data["currency"],
            availability=data.get("availability", "Unknown"),
            last_checked_at=datetime.utcnow(),
            is_active=True,
        )
        db.session.add(link)

    try:
        db.session.commit()
        try:
            from app.infrastructure.cache.item import invalidate_item_after_write

            invalidate_item_after_write(item.id)
        except Exception:
            logger.warning("Item cache invalidation failed for item id=%s", item.id)
        return item
    except Exception:
        db.session.rollback()
        logger.exception(f"Error storing Amazon item {data['asin']}")
        return None
