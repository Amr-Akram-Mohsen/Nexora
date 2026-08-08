"""
ProductInserter — source-agnostic SQLAlchemy insertion pipeline.

Accepts any ParsedProduct (produced by any BaseParser subclass) and
persists it to the database, handling:
    - Store auto-creation for well-known slugs
    - Duplicate detection via external_product_id → original_url fallback
    - Category and Brand get-or-create
    - Product slug uniqueness (appends -2, -3, … on collision)
    - ProductVariant, ProductImage, ProductSpecification, ProductStoreLink creation
    - Per-variant ProductStoreLink (each variant with a price gets its own link)

This class is intentionally store-agnostic.  Every source (AliExpress, Noon,
Amazon, …) feeds the same inserter via ParsedProduct.  Do not add any
source-specific logic here.

This class never raises — failures are logged and None is returned.
The caller is responsible for committing (or rolling back) the session.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.domains.product.models import (
    Product,
    ProductImage,
    ProductSpecification,
    ProductStoreLink,
    ProductVariant,
    Store,
)
from app.domains.taxonomy.models import Brand, Category
from app.shared.utils.slug import generate_slug
from app.integrations.commercial.schema import ParsedProduct, ParsedVariant

# Outside the app.* namespace so exceptions always reach the root handler,
# bypassing Flask's tag-based ingestion filters.
logger = logging.getLogger("commercial.inserter")

_DEFAULT_CATEGORY = "Uncategorized"

# Stores that can be auto-created on first import run.
# Only covers sources you actively use; others must be seeded separately.
_KNOWN_STORES: dict[str, dict] = {
    "aliexpress": {
        "name": "AliExpress",
        "website": "https://www.aliexpress.com",
        "country": "CN",
        "currency": "USD",
        "affiliate_network": "Manual",
    },
}


class ProductInserter:
    """
    Persists a ParsedProduct into the database within the given session.

    The caller is responsible for committing (or rolling back) the session.
    This keeps the inserter composable — you can wrap multiple inserts in
    one transaction if needed.

    Usage:
        inserter = ProductInserter(db.session)
        product = inserter.insert(parsed_product)
        db.session.commit()
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(self, parsed: ParsedProduct) -> Optional[Product]:
        """
        Insert one ParsedProduct.  Returns the created Product, or None when
        the product is a duplicate or insertion fails.
        """
        try:
            return self._insert(parsed)
        except Exception:
            logger.exception(
                "[ProductInserter] Failed to insert '%s'", parsed.name
            )
            self._session.rollback()
            return None

    # ------------------------------------------------------------------ #
    # Internal orchestration                                               #
    # ------------------------------------------------------------------ #

    def _insert(self, parsed: ParsedProduct) -> Optional[Product]:
        store = self._resolve_store(parsed.store_link.store_slug)
        if store is None:
            logger.warning(
                "[ProductInserter] Unknown store slug '%s', skipping '%s'",
                parsed.store_link.store_slug,
                parsed.name,
            )
            return None

        if self._is_duplicate(parsed, store):
            logger.info(
                "[ProductInserter] Duplicate skipped: '%s' (%s)",
                parsed.name,
                parsed.store_link.original_url,
            )
            return None

        category = self._resolve_category(parsed.category_name)
        brand = self._resolve_brand(parsed.brand_name)
        slug = self._unique_slug(parsed.name)

        product = Product(
            name=parsed.name,
            slug=slug,
            description=parsed.description,
            rating=parsed.rating,
            review_count=parsed.review_count,
            product_type=parsed.product_type,
            category=category,
            brand=brand,
            # Start every product in "pending"; the pipeline updates this
            # to "scraped" after successful insertion and search field population.
            ingestion_status="pending",
        )
        self._session.add(product)
        self._session.flush()  # product.id is now available

        self._add_images(product, parsed)
        variants = self._add_variants(product, parsed)
        self._add_specifications(product, parsed)
        self._add_store_links(parsed, variants, store)

        product.set_default_variant()
        self._session.flush()

        logger.info(
            "[ProductInserter] Inserted product id=%s slug='%s' name='%s'",
            product.id,
            product.slug,
            product.name,
        )
        return product

    # ------------------------------------------------------------------ #
    # Duplicate detection                                                  #
    # ------------------------------------------------------------------ #

    def _is_duplicate(self, parsed: ParsedProduct, store: Store) -> bool:
        """
        Check for an existing ProductStoreLink using:
          1. external_product_id (most reliable)
          2. original_url (fallback)
        """
        sl = parsed.store_link
        q = self._session.query(ProductStoreLink).filter_by(store_id=store.id)

        if sl.external_product_id:
            if q.filter_by(external_product_id=sl.external_product_id).first():
                return True

        if sl.original_url:
            if q.filter_by(original_url=sl.original_url).first():
                return True

        return False

    # ------------------------------------------------------------------ #
    # Store resolution                                                     #
    # ------------------------------------------------------------------ #

    def _resolve_store(self, slug: str) -> Optional[Store]:
        store = self._session.query(Store).filter_by(slug=slug).first()
        if store:
            return store

        cfg = _KNOWN_STORES.get(slug)
        if not cfg:
            return None

        store = Store(
            slug=slug,
            name=cfg["name"],
            website=cfg["website"],
            country=cfg["country"],
            currency=cfg["currency"],
            affiliate_network=cfg["affiliate_network"],
            is_active=True,
        )
        self._session.add(store)
        self._session.flush()
        logger.info("[ProductInserter] Auto-created store: %s", slug)
        return store

    # ------------------------------------------------------------------ #
    # Category & Brand resolution                                          #
    # ------------------------------------------------------------------ #

    def _resolve_category(self, name: Optional[str]) -> Category:
        # Use the established get_or_create pattern from taxonomy/models.py
        return Category.get_or_create(
            name=name or _DEFAULT_CATEGORY,
            session=self._session,
            is_leaf=True,
        )

    def _resolve_brand(self, name: Optional[str]) -> Optional[Brand]:
        if not name:
            return None
        return Brand.get_or_create(name, self._session)

    # ------------------------------------------------------------------ #
    # Slug uniqueness                                                      #
    # ------------------------------------------------------------------ #

    def _unique_slug(self, name: str) -> str:
        """Generate a slug, appending -2, -3, … if already taken."""
        base = generate_slug(name)
        slug = base
        counter = 2
        while self._session.query(Product).filter_by(slug=slug).first():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    # ------------------------------------------------------------------ #
    # Child record creation                                                #
    # ------------------------------------------------------------------ #

    def _add_images(self, product: Product, parsed: ParsedProduct) -> None:
        seen_urls: set[str] = set()
        for img in parsed.images:
            if not img.url or img.url in seen_urls:
                continue
            seen_urls.add(img.url)
            self._session.add(
                ProductImage(product_id=product.id, image_url=img.url, position=img.position)
            )

    def _add_variants(
        self, product: Product, parsed: ParsedProduct
    ) -> list[ProductVariant]:
        created: list[ProductVariant] = []
        for pv in parsed.variants:
            variant = self._create_variant(product, pv)
            self._session.add(variant)
            self._session.flush()  # variant.id available for variant images
            self._add_variant_images(variant, pv)
            created.append(variant)
        return created

    def _create_variant(self, product: Product, pv: ParsedVariant) -> ProductVariant:
        return ProductVariant(
            product_id=product.id,
            title=pv.title,
            sku=pv.sku or None,
            attributes=pv.attributes or None,
            price=pv.price,
            old_price=pv.old_price,
            currency=pv.currency,
            is_default=pv.is_default,
        )

    def _add_variant_images(
        self, variant: ProductVariant, pv: ParsedVariant
    ) -> None:
        seen_urls: set[str] = set()
        for pos, url in enumerate(pv.image_urls):
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            self._session.add(
                ProductImage(
                    product_id=variant.product_id,
                    variant_id=variant.id,
                    image_url=url,
                    position=pos,
                )
            )

    def _add_specifications(self, product: Product, parsed: ParsedProduct) -> None:
        for spec in parsed.specifications:
            self._session.add(
                ProductSpecification(
                    product_id=product.id,
                    category=spec.category,
                    spec_json=spec.spec_json,
                )
            )

    def _add_store_links(
        self,
        parsed: ParsedProduct,
        variants: list[ProductVariant],
        store: Store,
    ) -> None:
        """
        Create one ProductStoreLink per variant that has a price.

        Every link shares the same store, original_url, and external_product_id
        (those are product-level identifiers).  Pricing, old_price, currency, and
        availability are taken from the individual variant since the browser
        scraper captures those per-combination.

        If no variant has a price at all, fall back to creating a single link
        on the default (or first) variant using the store_link price, so that
        we at least record the product's existence in the store.
        """
        sl = parsed.store_link
        now = datetime.now(timezone.utc)

        variants_with_price = [v for v in variants if v.price is not None]

        if variants_with_price:
            for variant in variants_with_price:
                self._session.add(
                    ProductStoreLink(
                        variant_id=variant.id,
                        store_id=store.id,
                        external_product_id=sl.external_product_id,
                        original_url=sl.original_url,
                        # Affiliate URL starts as original_url; the affiliate
                        # workflow replaces it with the real deeplink later.
                        affiliate_url=sl.affiliate_url or sl.original_url,
                        price=variant.price,
                        old_price=variant.old_price,
                        currency=variant.currency or sl.currency,
                        availability=variant.availability,
                        is_active=True,
                        last_checked_at=now,
                    )
                )
        else:
            # Fallback: no variant has a price — attach to default/first variant
            # using store_link level pricing so we at least record the URL.
            default_variant = next((v for v in variants if v.is_default), None)
            if default_variant is None and variants:
                default_variant = variants[0]
            if default_variant is None:
                logger.warning(
                    "[ProductInserter] No variant available for store link on '%s'",
                    parsed.name,
                )
                return

            self._session.add(
                ProductStoreLink(
                    variant_id=default_variant.id,
                    store_id=store.id,
                    external_product_id=sl.external_product_id,
                    original_url=sl.original_url,
                    affiliate_url=sl.affiliate_url or sl.original_url,
                    price=sl.price,
                    old_price=sl.old_price,
                    currency=sl.currency,
                    availability=sl.availability,
                    is_active=True,
                    last_checked_at=now,
                )
            )
