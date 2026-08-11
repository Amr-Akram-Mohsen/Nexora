"""
Product-domain cache invalidation helpers.

Uses the same Flask-Caching backend as app.infrastructure.cache.memoize.
"""


def invalidate_item_page(product_id):
    """Drop cached static payload for one product detail page."""
    from app.application.product.public import get_item_page_data

    from app.core.extensions import cache

    cache.delete_memoized(get_item_page_data, product_id)


def invalidate_item_catalog_caches():
    """Drop cached catalog / home product listings (all filter variants)."""
    from app.domains.product.service.public.search import (
        get_filtered_items,
        _get_home_products_cached,
    )

    from app.core.extensions import cache

    cache.delete_memoized(get_filtered_items)
    cache.delete_memoized(_get_home_products_cached)
    cache.delete("home_page_data")


def invalidate_item_filter_options():
    """Drop cached sidebar filter option queries."""
    from app.domains.product.service.query import (
        get_distinct_product_types,
        get_distinct_stores,
    )
    from app.domains.taxonomy.service.query import (
        get_distinct_item_brands,
        get_distinct_item_categories,
    )

    from app.core.extensions import cache

    cache.delete_memoized(get_distinct_item_categories)
    cache.delete_memoized(get_distinct_item_brands)
    cache.delete_memoized(get_distinct_stores)
    cache.delete_memoized(get_distinct_product_types)


def invalidate_item_after_write(product_id=None):
    """
    Call after product ingest / admin update / price link change.
    """
    from app.core.extensions import cache
    if product_id is not None:
        invalidate_item_page(product_id)
    invalidate_item_catalog_caches()
    invalidate_item_filter_options()
    cache.delete("layout_context")
