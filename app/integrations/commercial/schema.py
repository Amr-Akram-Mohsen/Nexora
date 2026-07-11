"""
Normalized in-memory product structure.

Raw source HTML  →  Parser  →  ParsedProduct  →  ProductInserter  →  Database

These dataclasses are the shared contract between every source-specific
parser (AliExpressParser, SheinParser, …) and the source-agnostic
ProductInserter.  Nothing here is persisted directly.
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
