"""
ProductInserter — source-agnostic SQLAlchemy insertion pipeline.

Accepts any ParsedProduct (produced by any BaseParser subclass) and
persists it to the database, handling:
    - Store auto-creation for well-known slugs
    - Duplicate detection via external_product_id → original_url fallback
    - Category and Brand get-or-create
    - Product slug uniqueness (appends -2, -3, … on collision)
    - ProductVariant, ProductImage, ProductSpecification, ProductStoreLink creation

This class never raises — failures are logged and None is returned.
"""
from __future__ import annotations

import logging
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
from app.domains.taxonomy.models import Brand, Category, Source
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

    def insert(self, product: ParsedProduct) -> Optional[Product]:
        """
        Insert one ParsedProduct.  Returns the created Product, or None when
        the product is a duplicate or insertion fails.
        """
        try:
            return self._insert(product)
        except Exception:
            logger.exception(
                "[ProductInserter] Failed to insert '%s'", product.name
            )
            self._session.rollback()
            return None

    # ------------------------------------------------------------------ #
    # Internal orchestration                                               #
    # ------------------------------------------------------------------ #

    def _insert(self, product: ParsedProduct) -> Optional[Product]:
        store = self._resolve_store(product.store_link.store_slug)
        if store is None:
            logger.warning(
                "[ProductInserter] Unknown store slug '%s', skipping '%s'",
                product.store_link.store_slug,
                product.name,
            )
            return None

        if self._is_duplicate(product, store):
            logger.info(
                "[ProductInserter] Duplicate skipped: '%s' (%s)",
                product.name,
                product.store_link.original_url,
            )
            return None

        category = self._resolve_category(product.category_name)
        brand = self._resolve_brand(product.brand_name)
        slug = self._unique_slug(product.name)

        source = None
        if product.source_type:
            source_slug = generate_slug(product.source_type)
            source = self._session.query(Source).filter_by(slug=source_slug).first()
            if not source:
                source = Source(
                    name=product.source_type.capitalize(),
                    slug=source_slug,
                    domain=f"{source_slug}.com",
                    is_active=True
                )
                self._session.add(source)
                self._session.flush()

        product = Product(
            name=product.name,
            slug=slug,
            description=product.description,
            rating=product.rating,
            review_count=product.review_count,
            product_type=product.product_type,
            source_type=product.source_type,
            source_id=source.id if source else None,
            category=category,
            brand=brand,
        )
        self._session.add(product)
        self._session.flush()  # product.id is now available

        self._add_images(product, product)
        variants = self._add_variants(product, product)
        self._add_specifications(product, product)
        self._add_store_link(product, variants, product, store)

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

    def _is_duplicate(self, product: ParsedProduct, store: Store) -> bool:
        """
        Check for an existing ProductStoreLink using:
          1. external_product_id (most reliable)
          2. original_url (fallback)
        """
        sl = product.store_link
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
        target = name or _DEFAULT_CATEGORY
        slug = generate_slug(target)
        category = Category.get_by_slug(slug, self._session)
        if not category:
            category = Category.create(name=target, is_leaf=True)
            self._session.add(category)
            self._session.flush()
            logger.info("[ProductInserter] Created category: %s", target)
        return category

    def _resolve_brand(self, name: Optional[str]) -> Optional[Brand]:
        if not name:
            return None
        brand = Brand.get_or_create(name, self._session)
        return brand

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

    def _add_images(self, product: Product, product: ParsedProduct) -> None:
        for img in product.images:
            self._session.add(
                ProductImage(product_id=product.id, image_url=img.url, position=img.position)
            )

    def _add_variants(
        self, product: Product, product: ParsedProduct
    ) -> list[ProductVariant]:
        created: list[ProductVariant] = []
        for pv in product.variants:
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
            attributes=pv.attributes or None,
            price=pv.price,
            old_price=pv.old_price,
            currency=pv.currency,
            is_default=pv.is_default,
        )

    def _add_variant_images(
        self, variant: ProductVariant, pv: ParsedVariant
    ) -> None:
        for pos, url in enumerate(pv.image_urls):
            self._session.add(
                ProductImage(
                    product_id=variant.product_id,
                    variant_id=variant.id,
                    image_url=url,
                    position=pos,
                )
            )

    def _add_specifications(self, product: Product, product: ParsedProduct) -> None:
        for spec in product.specifications:
            self._session.add(
                ProductSpecification(
                    product_id=product.id,
                    category=spec.category,
                    spec_json=spec.spec_json,
                )
            )

    def _add_store_link(
        self,
        product: Product,
        variants: list[ProductVariant],
        product: ParsedProduct,
        store: Store,
    ) -> None:
        # Attach the store link to the default variant
        default_variant = next((v for v in variants if v.is_default), None)
        if default_variant is None and variants:
            default_variant = variants[0]
        if default_variant is None:
            logger.warning(
                "[ProductInserter] No variant available for store link on '%s'",
                product.name,
            )
            return

        sl = product.store_link
        self._session.add(
            ProductStoreLink(
                variant_id=default_variant.id,
                store_id=store.id,
                external_product_id=sl.external_product_id,
                original_url=sl.original_url,
                affiliate_url=sl.affiliate_url,
                price=sl.price,
                old_price=sl.old_price,
                currency=sl.currency,
                availability=sl.availability,
                is_active=True,
            )
        )
