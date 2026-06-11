"""
Recommendation service package.

Exposes all public recommendation query functions from a single import point.
"""
from .content import (
    get_related_contents_scored,
    get_trending_contents_scored,
    get_editors_picks,
)
from .items import (
    get_items_for_content,
    get_trending_items,
    get_popular_items_by_brand,
    get_contents_for_item,
)

__all__ = [
    "get_related_contents_scored",
    "get_trending_contents_scored",
    "get_editors_picks",
    "get_items_for_content",
    "get_trending_items",
    "get_popular_items_by_brand",
    "get_contents_for_item",
]
