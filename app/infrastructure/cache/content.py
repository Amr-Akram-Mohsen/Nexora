"""
Content-domain cache invalidation helpers.

Uses the shared Flask-Caching backend through app.infrastructure.cache.
"""


def invalidate_content_page(content_id):
    """Drop cached static payloads for one content detail page."""
    from app.application.content.get_content_page import get_content_page_static_data
    from app.application.content.query_service import get_related_contents_cached
    from app.core.extensions import cache

    cache.delete_memoized(get_content_page_static_data, content_id)
    cache.delete_memoized(get_related_contents_cached, content_id)


def invalidate_content_listing_caches():
    """Drop cached homepage, feed, and trending content listings."""
    from app.application.content.query_service import (
        get_contents_render_cached,
        get_filtered_contents_cached,
        get_trending_contents_cached,
    )
    from app.core.extensions import cache

    cache.delete("home_page_data")
    cache.delete_memoized(get_contents_render_cached)
    cache.delete_memoized(get_filtered_contents_cached)
    cache.delete_memoized(get_trending_contents_cached)


def invalidate_content_filter_options():
    """Drop cached section filter option queries."""
    from app.domains.system.service.query import (
        _cached_attributes_for_section,
        get_relationships_for_section,
        get_types_for_section,
    )
    from app.core.extensions import cache

    cache.delete_memoized(get_relationships_for_section)
    cache.delete_memoized(get_types_for_section)
    cache.delete_memoized(_cached_attributes_for_section)


def invalidate_content_after_write(content_id=None):
    """Call after content ingest, publish changes, or taxonomy updates."""
    if content_id is not None:
        invalidate_content_page(content_id)
    invalidate_content_listing_caches()
    invalidate_content_filter_options()
