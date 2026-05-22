"""
Item-domain cache invalidation helpers.

Uses the same Flask-Caching backend as app.infrastructure.cache.memoize.
"""


def invalidate_item_page(item_id):
    """Drop cached static payload for one item detail page."""
    from app.application.item.get_item_page import get_item_static_data

    from app.core.extensions import cache

    cache.delete_memoized(get_item_static_data, item_id)


def invalidate_item_catalog_caches():
    """Drop cached catalog / home item listings (all filter variants)."""
    from app.domains.item.service.query import (
        get_filtered_items,
        get_filtered_items_for_home,
    )

    from app.core.extensions import cache

    cache.delete_memoized(get_filtered_items)
    cache.delete_memoized(get_filtered_items_for_home)


def invalidate_item_filter_options():
    """Drop cached sidebar filter option queries."""
    from app.domains.item.service.query import (
        get_distinct_item_types,
        get_distinct_stores,
    )
    from app.domains.system.service.query import (
        get_distinct_item_brands,
        get_distinct_item_categories,
    )

    from app.core.extensions import cache

    cache.delete_memoized(get_distinct_item_categories)
    cache.delete_memoized(get_distinct_item_brands)
    cache.delete_memoized(get_distinct_stores)
    cache.delete_memoized(get_distinct_item_types)


def invalidate_item_after_write(item_id=None):
    """
    Call after item ingest / admin update / price link change.
    """
    if item_id is not None:
        invalidate_item_page(item_id)
    invalidate_item_catalog_caches()
