"""
Normalized in-memory product structure.

Raw source HTML  →  Parser  →  ParsedProduct  →  ProductInserter  →  Database

These dataclasses are the shared contract between every source-specific
parser (AliExpressParser, NoonParser, AmazonParser, …) and the
source-agnostic ProductInserter.  Nothing here is persisted directly.

Discovery metadata (discovery_source, discovery_keyword, etc.) is purely
informational — it is logged and stored in ProductDiscoveryQueue but is NOT
written to the Product model, keeping the product domain clean.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class ParsedImage:
    url: str
    position: int = 0


@dataclass
class ParsedVariant:
    title: Optional[str]
    attributes: dict[str, str]
    price: Optional[Decimal]
    old_price: Optional[Decimal]
    currency: Optional[str]
    is_default: bool = False
    image_urls: list[str] = field(default_factory=list)
    # Populated by the browser scraper; None when using static HTML parsing.
    sku: Optional[str] = None
    # AliExpress internal SKU/SKU-col ID (from data-sku-col attribute).
    # Used for combination URL construction and deduplication.
    sku_id: Optional[str] = None
    # Per-variant availability.  Defaults to "InStock" when not determinable.
    availability: str = "InStock"


@dataclass
class ParsedStoreLink:
    store_slug: str
    affiliate_url: str
    original_url: str
    external_product_id: Optional[str]
    price: Optional[Decimal]
    old_price: Optional[Decimal]
    currency: Optional[str]
    availability: str = "InStock"


@dataclass
class ParsedSpecification:
    """A flat key-value group stored as JSON under a named category."""
    category: str
    spec_json: dict[str, str]


@dataclass
class ParsedProduct:
    name: str
    description: Optional[str]
    brand_name: Optional[str]
    category_name: Optional[str]
    product_type: Optional[str]
    source_type: str
    rating: Optional[float]
    review_count: Optional[int]
    images: list[ParsedImage]
    variants: list[ParsedVariant]
    specifications: list[ParsedSpecification]
    store_link: ParsedStoreLink
    # ── Discovery provenance ─────────────────────────────────────────
    # These fields are informational only.  They describe how this URL
    # was discovered and are stored in ProductDiscoveryQueue, not in Product.
    discovery_source: Optional[str] = None       # "category" | "search" | "manual" | "newsletter"
    discovery_keyword: Optional[str] = None      # the search keyword that led here
    discovery_category_path: Optional[str] = None  # e.g. "Electronics > Phones"
