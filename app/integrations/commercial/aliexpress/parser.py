"""
AliExpressParser — converts raw AliExpress HTML into a ParsedProduct.

Input format (one element of the batch JSON):
    {
        "store":               "aliexpress",
        "product_url":         "https://www.aliexpress.com/item/1005010507405338.html",
        "affiliate_url":       "https://...",
        "product_info_html":   "<div class='pdp-info'>...</div>",
        "specifications_html": "<ul class='specification--list...'>...</ul>"
    }

Parsing is intentionally defensive — every field is optional except the
product title.  Missing data becomes None / empty list rather than an error.
"""
from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bs4 import BeautifulSoup

from app.shared.sanitizer import sanitize_text
from app.integrations.commercial.base_parser import BaseParser
from app.integrations.commercial.schema import (
    ParsedImage,
    ParsedProduct,
    ParsedSpecification,
    ParsedStoreLink,
    ParsedVariant,
)

logger = logging.getLogger(__name__)

SOURCE_SLUG = "aliexpress"

# Matches "SAR656.42", "AED 199", "USD12.50"
_PRICE_WITH_CUR_RE = re.compile(r"([A-Z]{2,3})\s*([\d,]+\.?\d*)")
# Matches a bare number "941.13" or "1,000"
_BARE_NUM_RE = re.compile(r"([\d,]+\.?\d*)")
# Extracts AliExpress item ID from URL
_ITEM_ID_RE = re.compile(r"/item/(\d+)\.html")


class AliExpressParser(BaseParser):
    """Parses one AliExpress product entry from the batch JSON file."""

    source_slug = SOURCE_SLUG

    def parse(self, raw: dict) -> Optional[ParsedProduct]:
        try:
            return self._parse(raw)
        except Exception:
            logger.exception(
                "[AliExpress] Unexpected error parsing product: %s",
                raw.get("product_url", "unknown"),
            )
            return None

    # ------------------------------------------------------------------ #
    # Top-level orchestration                                              #
    # ------------------------------------------------------------------ #

    def _parse(self, raw: dict) -> Optional[ParsedProduct]:
        product_url: str = raw.get("product_url", "")
        affiliate_url: str = raw.get("affiliate_url") or product_url
        info_html: str = raw.get("product_info_html", "")
        spec_html: str = raw.get("specifications_html", "")

        if not info_html:
            logger.warning(
                "[AliExpress] Skipping entry with no product_info_html: %s", product_url
            )
            return None

        info = BeautifulSoup(info_html, "html.parser")
        spec = BeautifulSoup(spec_html, "html.parser") if spec_html else None

        name = self._parse_title(info)
        if not name:
            logger.warning(
                "[AliExpress] Could not extract title, skipping: %s", product_url
            )
            return None

        rating, review_count = self._parse_reviewer(info)
        price, old_price, currency = self._parse_price(info)
        images = self._parse_images(info)
        variants = self._parse_variants(info, price, old_price, currency)
        specs, brand_name, category_name = self._parse_specifications(spec)
        external_item_id = self._extract_item_id(product_url, info)

        store_link = ParsedStoreLink(
            store_slug=SOURCE_SLUG,
            affiliate_url=affiliate_url,
            original_url=product_url,
            external_item_id=external_item_id,
            price=price,
            old_price=old_price,
            currency=currency,
            availability="InStock",
        )

        return ParsedProduct(
            name=name,
            description=None,
            brand_name=brand_name,
            category_name=category_name,
            item_type=None,
            source_type=SOURCE_SLUG,
            rating=rating,
            review_count=review_count,
            images=images,
            variants=variants,
            specifications=specs,
            store_link=store_link,
        )

    # ------------------------------------------------------------------ #
    # Field-level parsers                                                  #
    # ------------------------------------------------------------------ #

    def _parse_title(self, soup: BeautifulSoup) -> Optional[str]:
        tag = soup.find("h1", attrs={"data-pl": "product-title"})
        if not tag:
            tag = soup.find("h1")
        return sanitize_text(tag.get_text()) if tag else None

    def _parse_reviewer(
        self, soup: BeautifulSoup
    ) -> tuple[Optional[float], Optional[int]]:
        rating: Optional[float] = None
        review_count: Optional[int] = None

        # The reviewer block contains the star rating and review count
        wrap = soup.find(class_=re.compile(r"reviewer--wrap|reviewer--box"))
        if not wrap:
            return rating, review_count

        # Rating value is inside a <strong> tag: "\xa0\xa04.8\xa0\xa0"
        strong = wrap.find("strong")
        if strong:
            cleaned = strong.get_text().replace("\xa0", "").replace("&nbsp;", "").strip()
            try:
                rating = float(cleaned)
            except ValueError:
                pass

        # "219 Reviews" → 219
        reviews_tag = wrap.find(class_=re.compile(r"reviewer--reviews"))
        if reviews_tag:
            m = _BARE_NUM_RE.search(reviews_tag.get_text().replace(",", ""))
            if m:
                try:
                    review_count = int(m.group(1).replace(",", ""))
                except ValueError:
                    pass

        return rating, review_count

    def _parse_price(
        self, soup: BeautifulSoup
    ) -> tuple[Optional[Decimal], Optional[Decimal], Optional[str]]:
        price: Optional[Decimal] = None
        old_price: Optional[Decimal] = None
        currency: Optional[str] = None

        current_tag = soup.find(class_=re.compile(r"price-default--current"))
        if current_tag:
            price, currency = self._split_price(current_tag.get_text())

        original_tag = soup.find(class_=re.compile(r"price-default--original"))
        if original_tag:
            bdi = original_tag.find("bdi")
            raw_text = bdi.get_text() if bdi else original_tag.get_text()
            val, cur = self._split_price(raw_text)
            old_price = val
            if not currency and cur:
                currency = cur

        return price, old_price, currency

    def _split_price(self, text: str) -> tuple[Optional[Decimal], Optional[str]]:
        """Parse 'SAR656.42' or '941.13' into (Decimal, currency_or_None)."""
        text = text.strip()
        m = _PRICE_WITH_CUR_RE.search(text)
        if m:
            try:
                return Decimal(m.group(2).replace(",", "")), m.group(1)
            except InvalidOperation:
                pass
        # Bare number (old price without currency prefix)
        m2 = _BARE_NUM_RE.search(text.replace(",", ""))
        if m2:
            try:
                return Decimal(m2.group(1)), None
            except InvalidOperation:
                pass
        return None, None

    def _parse_images(self, soup: BeautifulSoup) -> list[ParsedImage]:
        """
        Collect slider thumbnail images, deduplicate, and upgrade to high-res.
        Items containing a video icon are skipped (video thumbnail).
        """
        seen: set[str] = set()
        images: list[ParsedImage] = []

        for item in soup.find_all(class_=re.compile(r"slider--item")):
            if item.find(class_=re.compile(r"videoIcon|video--")):
                continue
            img_wrap = item.find(class_=re.compile(r"slider--img"))
            if not img_wrap:
                continue
            img = img_wrap.find("img")
            if not img or not img.get("src"):
                continue
            url = self._upgrade_image_url(img["src"])
            if url and url not in seen:
                seen.add(url)
                images.append(ParsedImage(url=url, position=len(images)))

        return images

    def _upgrade_image_url(self, url: str) -> str:
        """
        Convert AliExpress thumbnail URL to 960×960 version.
        e.g. _220x220q75.jpg_.avif  →  _960x960q75.jpg_.avif
        """
        return re.sub(
            r"_(\d+)x(\d+)(q\d+)?(\.\w+_\.avif)$",
            lambda m: f"_960x960{m.group(3) or ''}{m.group(4)}",
            url,
        )

    def _parse_variants(
        self,
        soup: BeautifulSoup,
        price: Optional[Decimal],
        old_price: Optional[Decimal],
        currency: Optional[str],
    ) -> list[ParsedVariant]:
        """
        Extract colour / SKU variants from the SKU selector widget.
        Falls back to a single default variant when no selector is present.
        All variants share the same price because AliExpress HTML only
        exposes the currently-selected variant's price without JS rendering.
        """
        sku_wrap = soup.find(class_=re.compile(r"sku--wrap"))
        if not sku_wrap:
            return [self._make_default_variant(price, old_price, currency)]

        variants: list[ParsedVariant] = []

        for item_wrap in sku_wrap.find_all(class_=re.compile(r"sku-item--wrap")):
            title_tag = item_wrap.find(class_=re.compile(r"sku-item--title"))
            dimension_text = sanitize_text(title_tag.get_text()) if title_tag else ""
            # "Color: Black" → dim_key = "color"
            dim_key = (
                dimension_text.split(":")[0].strip().lower()
                if ":" in dimension_text
                else "variant"
            )

            for idx, sku_item in enumerate(
                item_wrap.find_all(attrs={"data-sku-col": True})
            ):
                img = sku_item.find("img")
                attr_value = (
                    img["alt"].strip() if img and img.get("alt") else f"Option {idx + 1}"
                )
                img_url = (
                    self._upgrade_image_url(img["src"])
                    if img and img.get("src")
                    else None
                )
                is_selected = bool(
                    re.search(r"sku-item--selected", " ".join(sku_item.get("class", [])))
                )
                variants.append(
                    ParsedVariant(
                        title=attr_value,
                        attributes={dim_key: attr_value},
                        price=price,
                        old_price=old_price,
                        currency=currency,
                        is_default=is_selected,
                        image_urls=[img_url] if img_url else [],
                    )
                )

        if not variants:
            return [self._make_default_variant(price, old_price, currency)]

        # Guarantee exactly one default
        if not any(v.is_default for v in variants):
            variants[0].is_default = True

        return variants

    def _make_default_variant(
        self,
        price: Optional[Decimal],
        old_price: Optional[Decimal],
        currency: Optional[str],
    ) -> ParsedVariant:
        return ParsedVariant(
            title=None,
            attributes={},
            price=price,
            old_price=old_price,
            currency=currency,
            is_default=True,
        )

    def _parse_specifications(
        self, soup: Optional[BeautifulSoup]
    ) -> tuple[list[ParsedSpecification], Optional[str], Optional[str]]:
        """
        Parse the AliExpress specification list into a flat dict stored as JSON.
        Also extracts 'Brand Name' and 'Category' which are promoted to the
        top-level product fields rather than kept inside spec_json.

        Returns: (specs_list, brand_name, category_name)
        """
        if soup is None:
            return [], None, None

        spec_dict: dict[str, str] = {}
        for prop in soup.find_all(class_=re.compile(r"specification--prop")):
            key_tag = prop.find(class_=re.compile(r"specification--title"))
            val_tag = prop.find(class_=re.compile(r"specification--desc"))
            if not key_tag or not val_tag:
                continue
            key = sanitize_text(key_tag.get_text())
            val = sanitize_text(val_tag.get_text())
            if key and val:
                spec_dict[key] = val

        # Promote well-known keys to top-level product fields
        brand_name = spec_dict.pop("Brand Name", None)
        category_name = spec_dict.pop("Category", None)

        specs: list[ParsedSpecification] = []
        if spec_dict:
            specs.append(ParsedSpecification(category="general", spec_json=spec_dict))

        return specs, brand_name, category_name

    def _extract_item_id(self, url: str, soup: BeautifulSoup) -> Optional[str]:
        """Extract AliExpress item ID from URL, falling back to HTML data attrs."""
        m = _ITEM_ID_RE.search(url)
        if m:
            return m.group(1)
        # Some page variants store it in a data attribute
        tag = soup.find(attrs={"ae_object_value": True})
        if tag:
            return tag["ae_object_value"]
        return None
