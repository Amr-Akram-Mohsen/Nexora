"""
AliExpressParser — converts raw AliExpress HTML into a ParsedProduct.

Input format (one element of the batch JSON):
    {
        "store":         "aliexpress",
        "product_url":   "https://www.aliexpress.com/item/1005010507405338.html",
        "affiliate_url": "https://...",
        "html":          "<html>...</html>"
    }

Two parsing modes are supported:

1. parse(raw)  — static HTML only.
   Used by the file-based run_import.py workflow and for dry-run testing.
   Variants all share the currently-selected price from the HTML.

2. parse_with_variants(raw, variant_combinations)  — HTML + live scrape data.
   Used by the automated pipeline (pipeline.py).
   Variant prices are real values captured by VariantWalker clicking each SKU
   combination.  Falls back to static parsing when variant_combinations is empty.

Parsing is intentionally defensive — every field is optional except the
product title.  Missing data becomes None / empty list rather than an error.
"""
from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

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
from app.integrations.commercial.aliexpress.utils import (
    split_price,
    upgrade_image_url,
    extract_product_id,
)
from app.integrations.commercial.aliexpress.normalizers import (
    normalize_product_name,
    normalize_brand_name,
    normalize_category_name,
)


if TYPE_CHECKING:
    from app.integrations.commercial.aliexpress.scraper.variant_walker import (
        ScrapedVariantCombination,
    )

logger = logging.getLogger(__name__)

SOURCE_SLUG = "aliexpress"

# Spec keys that are promoted to top-level product fields rather than kept inside spec_json.
_PROMOTED_SPEC_KEYS = {"Brand Name", "Category"}

# Ordered list of (lowercase_keyword, spec_group_name) for case-insensitive substring matching.
_SPEC_SUBSTRING_MAP: list[tuple[str, str]] = [
    # Display
    ("screen size", "display"),
    ("display", "display"),
    ("resolution", "display"),
    ("refresh rate", "display"),
    # Platform / CPU
    ("ram", "platform"),
    ("internal memory", "platform"),
    ("processor", "platform"),
    ("cpu", "platform"),
    ("operating system", "platform"),
    ("chipset", "platform"),
    # Battery
    ("battery", "battery"),
    ("charging", "battery"),
    # Camera
    ("camera", "camera"),
    # Connectivity
    ("connectivity", "connectivity"),
    ("bluetooth", "connectivity"),
    ("wi-fi", "connectivity"),
    ("wifi", "connectivity"),
    ("nfc", "connectivity"),
    ("usb", "connectivity"),
    ("sim", "connectivity"),
    # Physical
    ("dimensions", "physical"),
    ("weight", "physical"),
    ("color", "physical"),
    ("material", "physical"),
    ("water resistance", "physical"),
]


def _get_tag_text_or_title(tag) -> str:
    """Extract clean text from tag, preferring title attribute when present (e.g. truncated titles)."""
    if not tag:
        return ""
    title_attr = tag.get("title")
    if title_attr and isinstance(title_attr, str) and title_attr.strip():
        return sanitize_text(title_attr)
    return sanitize_text(tag.get_text())


def _get_image_src(img) -> Optional[str]:
    """Extract image URL checking multiple lazy-load attributes in priority order."""
    if not img:
        return None
    for attr in ("src", "data-src", "data-lazy-src", "data-img", "data-image"):
        val = img.get(attr)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return None


class AliExpressParser(BaseParser):
    """Parses one AliExpress product entry from raw HTML."""

    source_slug = SOURCE_SLUG

    # ------------------------------------------------------------------ #
    # Public interface                                                   #
    # ------------------------------------------------------------------ #

    def parse(self, raw: dict) -> Optional[ParsedProduct]:
        """Parse from static HTML only."""
        try:
            return self._parse(raw, variant_combinations=None)
        except Exception:
            logger.exception(
                "[AliExpress] Unexpected error parsing product: %s",
                raw.get("product_url", "unknown"),
            )
            return None

    def parse_with_variants(
        self,
        raw: dict,
        variant_combinations: list["ScrapedVariantCombination"],
    ) -> Optional[ParsedProduct]:
        """Parse from HTML enriched with browser-scraped variant data."""
        try:
            return self._parse(raw, variant_combinations=variant_combinations or None)
        except Exception:
            logger.exception(
                "[AliExpress] Unexpected error parsing product (with variants): %s",
                raw.get("product_url", "unknown"),
            )
            return None

    # ------------------------------------------------------------------ #
    # Top-level orchestration                                           #
    # ------------------------------------------------------------------ #

    def _parse(
        self,
        raw: dict,
        *,
        variant_combinations: Optional[list] = None,
    ) -> Optional[ParsedProduct]:
        product_url: str = raw.get("product_url", "")
        affiliate_url: str = raw.get("affiliate_url") or product_url

        html: str = raw.get("html", "")
        if not html:
            logger.warning("[AliExpress] Skipping entry with no HTML: %s", product_url)
            return None

        soup = BeautifulSoup(html, "html.parser")
        info = soup.find("div", class_="pdp-info") or soup
        spec_block = soup.find("ul", class_=re.compile(r"\bspecification--list\b")) or soup.find(id="nav-specification") or soup.find(attrs={"data-pl": "product-specs"}) or soup.find(class_=re.compile(r"\bspecification--wrap\b"))


        name = self._parse_title(info)
        if not name:
            logger.warning("[AliExpress] Could not extract title, skipping: %s", product_url)
            return None

        rating, review_count = self._parse_reviewer(info)
        price, old_price, currency = self._parse_price(info)
        images = self._parse_images(info)
        specs, brand_name, category_name = self._parse_specifications(spec_block)
        external_product_id = extract_product_id(product_url) or self._extract_product_id_from_html(info)

        # Build variants — prefer live scrape data when available
        if variant_combinations:
            variants = self._build_variants_from_scrape(variant_combinations)
        else:
            variants = self._parse_variants(info, price, old_price, currency)

        store_link = ParsedStoreLink(
            store_slug=SOURCE_SLUG,
            affiliate_url=affiliate_url,
            original_url=product_url,
            external_product_id=external_product_id,
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
            product_type=None,
            source_type=SOURCE_SLUG,
            rating=rating,
            review_count=review_count,
            images=images,
            variants=variants,
            specifications=specs,
            store_link=store_link,
        )

    # ------------------------------------------------------------------ #
    # Field-level parsers                                                #
    # ------------------------------------------------------------------ #

    def _parse_title(self, soup: BeautifulSoup) -> Optional[str]:
        tag = soup.find("h1", attrs={"data-pl": "product-title"})
        if not tag:
            tag = soup.find("h1", attrs={"data-sku-title": True})
        if not tag:
            tag = soup.find("h1")
        title = _get_tag_text_or_title(tag) if tag else None
        return normalize_product_name(title) if title else None

    def _parse_reviewer(
        self, soup: BeautifulSoup
    ) -> tuple[Optional[float], Optional[int]]:
        rating: Optional[float] = None
        review_count: Optional[int] = None

        # 1. Parse Rating independently using numeric regex (values between 1.0 and 5.0)
        for tag_name in ("strong", "span", "div"):
            for elem in soup.find_all(tag_name, class_=re.compile(r"\breviewer--|\brating--|\bscore--")):
                text = _get_tag_text_or_title(elem)
                m = re.search(r"\b([1-5](?:\.\d{1,2})?)\b", text)
                if m:
                    try:
                        val = float(m.group(1))
                        if 1.0 <= val <= 5.0:
                            rating = val
                            break
                    except ValueError:
                        pass
            if rating is not None:
                break

        # 2. Parse Review Count independently
        reviews_tag = soup.find(class_=re.compile(r"\breviewer--reviews\b")) or soup.find(attrs={"data-pl": "reviews-count"})
        if reviews_tag:
            from app.integrations.commercial.aliexpress.utils import _BARE_NUM_RE
            m = _BARE_NUM_RE.search(_get_tag_text_or_title(reviews_tag).replace(",", ""))
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

        # Priority selectors for current sale price
        current_selectors = [
            re.compile(r"\bprice-default--current\b"),
            re.compile(r"\bprice--current\b"),
            re.compile(r"\bprice--sale\b"),
            re.compile(r"\buniform-banner-price\b"),
            re.compile(r"\bprice--discount\b"),
        ]
        for sel in current_selectors:
            current_tag = soup.find(class_=sel) or soup.find(attrs={"data-pl": "product-price"})
            if current_tag:
                price, currency = split_price(_get_tag_text_or_title(current_tag))
                if price is not None:
                    break

        # Priority selectors for original / old price
        original_selectors = [
            re.compile(r"\bprice-default--original\b"),
            re.compile(r"\bprice--original\b"),
            re.compile(r"\bprice--was\b"),
            re.compile(r"\bprice--old\b"),
        ]
        for sel in original_selectors:
            original_tag = soup.find(class_=sel)
            if original_tag:
                bdi = original_tag.find("bdi")
                raw_text = _get_tag_text_or_title(bdi) if bdi else _get_tag_text_or_title(original_tag)
                val, cur = split_price(raw_text)
                if val is not None:
                    old_price = val
                    if not currency and cur:
                        currency = cur
                    break

        return price, old_price, currency

    def _parse_images(self, soup: BeautifulSoup) -> list[ParsedImage]:
        seen: set[str] = set()
        images: list[ParsedImage] = []

        # Match all slider item container variations (slider--product, slider--item, slider--box, slider--image)
        slider_items = soup.find_all(class_=re.compile(r"\bslider--(?:product|item|box|image)\b")) or soup.find_all(class_=re.compile(r"\bslider--\b"))
        for product in slider_items:
            if product.find(class_=re.compile(r"\bvideoIcon\b|\bvideo--\b")):
                continue
            img = product.find("img") if product.name != "img" else product
            if not img:
                continue
            raw_src = _get_image_src(img)
            if not raw_src:
                continue
            # Normalize first, then deduplicate
            url = upgrade_image_url(raw_src)
            if url and url not in seen:
                seen.add(url)
                images.append(ParsedImage(url=url, position=len(images)))

        # Fallback: check main product image or semantic attributes
        if not images:
            main = soup.find(class_=re.compile(r"\bpdp-main-image\b|\bmagnifier--image\b")) or soup.find(attrs={"data-pl": "main-image"})
            if main:
                img_target = main if main.name == "img" else main.find("img")
                raw_src = _get_image_src(img_target) if img_target else None
                if raw_src:
                    url = upgrade_image_url(raw_src)
                    if url and url not in seen:
                        images.append(ParsedImage(url=url, position=0))

        return images


    def _parse_variants(
        self,
        soup: BeautifulSoup,
        price: Optional[Decimal],
        old_price: Optional[Decimal],
        currency: Optional[str],
    ) -> list[ParsedVariant]:
        sku_wrap = soup.find(class_=re.compile(r"\bsku--wrap\b")) or soup.find(attrs={"data-sku-row": True})
        if not sku_wrap:
            return [self._make_default_variant(price, old_price, currency)]

        variants: list[ParsedVariant] = []

        for item_wrap in sku_wrap.find_all(class_=re.compile(r"\bsku-product--wrap\b")):
            title_tag = item_wrap.find(class_=re.compile(r"\bsku-product--title\b"))
            dimension_text = _get_tag_text_or_title(title_tag) if title_tag else ""

            # Determine dimension key defensively
            if ":" in dimension_text:
                dim_key = dimension_text.split(":")[0].strip().lower()
            else:
                first_img = item_wrap.find("img")
                alt_text = first_img.get("alt", "").lower() if first_img else ""
                if any(k in alt_text for k in ("color", "colour")):
                    dim_key = "color"
                elif any(k in alt_text for k in ("storage", "capacity", "memory")):
                    dim_key = "storage"
                elif "package" in alt_text:
                    dim_key = "package"
                elif "bundle" in alt_text:
                    dim_key = "bundle"
                elif "model" in alt_text:
                    dim_key = "model"
                else:
                    dim_key = "variant"

            for idx, sku_item in enumerate(
                item_wrap.find_all(attrs={"data-sku-col": True}) or item_wrap.find_all(class_=re.compile(r"\bsku-product--item\b"))
            ):
                img = sku_item.find("img")
                attr_value = (
                    img["alt"].strip() if img and img.get("alt") else f"Option {idx + 1}"
                )
                raw_img_src = _get_image_src(img) if img else None
                img_url = upgrade_image_url(raw_img_src) if raw_img_src else None

                is_selected = bool(
                    re.search(r"\bsku-product--selected\b", " ".join(sku_item.get("class", [])))
                )
                # Detect out-of-stock / sold out items with component prefix matching
                is_unavailable = bool(
                    re.search(
                        r"\bsku-product--(?:disabled|unavailable|soldOut)\b",
                        " ".join(sku_item.get("class", [])),
                        re.IGNORECASE,
                    )
                )
                sku_id = sku_item.get("data-sku-col") or sku_item.get("data-sku-id")

                variants.append(
                    ParsedVariant(
                        title=attr_value,
                        attributes={dim_key: attr_value},
                        price=price,
                        old_price=old_price,
                        currency=currency,
                        is_default=is_selected,
                        image_urls=[img_url] if img_url else [],
                        sku_id=sku_id,
                        availability="OutOfStock" if is_unavailable else "InStock",
                    )
                )

        if not variants:
            return [self._make_default_variant(price, old_price, currency)]

        if not any(v.is_default for v in variants):
            variants[0].is_default = True

        return variants

    def _build_variants_from_scrape(
        self, combinations: list
    ) -> list[ParsedVariant]:
        if not combinations:
            return []

        variants: list[ParsedVariant] = []
        has_default = False

        for combo in combinations:
            is_default = combo.is_selected and not has_default
            if is_default:
                has_default = True
            variants.append(
                ParsedVariant(
                    title=None,
                    attributes=combo.attributes,
                    price=combo.price,
                    old_price=combo.old_price,
                    currency=combo.currency,
                    is_default=is_default,
                    image_urls=[combo.image_url] if combo.image_url else [],
                    sku_id=combo.sku_id,
                    availability=combo.availability,
                )
            )

        if variants and not has_default:
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
        if soup is None:
            return [], None, None

        raw_dict: dict[str, str] = {}
        for prop in soup.find_all(class_=re.compile(r"\bspecification--prop\b")):
            key_tag = prop.find(class_=re.compile(r"\bspecification--title\b"))
            val_tag = prop.find(class_=re.compile(r"\bspecification--desc\b"))
            if not key_tag or not val_tag:
                continue
            key = _get_tag_text_or_title(key_tag)
            val = _get_tag_text_or_title(val_tag)
            if key and val:
                raw_dict[key] = val

        # Promote well-known top-level fields
        raw_brand = raw_dict.pop("Brand Name", None)
        raw_cat = raw_dict.pop("Category", None)

        brand_name = normalize_brand_name(raw_brand) if raw_brand else None
        category_name = normalize_category_name(raw_cat) if raw_cat else None

        # Substring-based group mapping
        groups: dict[str, dict[str, str]] = {}
        for key, val in raw_dict.items():
            key_lower = key.lower()
            group = "general"
            for keyword, group_name in _SPEC_SUBSTRING_MAP:
                if keyword in key_lower:
                    group = group_name
                    break
            groups.setdefault(group, {})[key] = val

        specs: list[ParsedSpecification] = [
            ParsedSpecification(category=group_name, spec_json=spec_data)
            for group_name, spec_data in groups.items()
            if spec_data
        ]

        return specs, brand_name, category_name

    def _extract_product_id_from_html(self, soup: BeautifulSoup) -> Optional[str]:
        tag = soup.find(attrs={"ae_object_value": True})
        if tag:
            return tag["ae_object_value"]
        return None

