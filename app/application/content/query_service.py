from app.infrastructure import cache
from app.infrastructure.cache import filters_from_normalized
from app.domains.content.service import query as domain_query
from app.core.extensions import db

@cache.memoize(timeout=600)
def get_contents_render_cached(filter_by_columns: tuple = ('section',), filter_values: tuple = (None,), rows_count=None, exclude_ids: tuple | None = None):
    return domain_query.get_contents_render(filter_by_columns, filter_values, rows_count, exclude_ids)

@cache.memoize(timeout=3600)
def get_related_contents_cached(content_id, limit=6):
    return domain_query.get_related_contents(content_id, limit)

@cache.memoize(timeout=300)
def get_trending_contents_cached(limit=6, days=7, section_ids=None, exclude_ids=None):
    return domain_query.get_trending_contents(limit=limit, days=days, section_ids=section_ids, exclude_ids=exclude_ids)

def get_filtered_contents(section_id, active_filters, allowed_filters, page=1, per_page=24):
    return domain_query.get_filtered_contents(section_id, active_filters, allowed_filters, page, per_page)


@cache.memoize(timeout=300)
def get_filtered_contents_cached(
    section_id, active_filters_key, allowed_filters_key, page=1, per_page=24
):
    active_filters = filters_from_normalized(active_filters_key)
    allowed_filters = list(allowed_filters_key)
    return domain_query.get_filtered_contents(
        section_id, active_filters, allowed_filters, page, per_page
    )


@cache.memoize(timeout=3600)
def get_carousel_contents_cached(active_filters_key, exclude_ids_key=None, limit=6):
    """
    Fetches contents for a carousel component based on specific filters (e.g. topic, brand, author).
    Limits to `limit` items, and excludes `exclude_ids_key`.
    """
    active_filters = filters_from_normalized(active_filters_key)
    allowed_filters = list(active_filters.keys())
    
    # We fetch limit + 1 just in case one item is excluded, 
    # though it's better to fetch a few more if we have multiple exclusions.
    # But since get_filtered_contents doesn't support exclude_ids yet, we filter post-query.
    res = domain_query.get_filtered_contents(
        None, active_filters, allowed_filters, page=1, per_page=limit + 5
    )
    
    contents = res.get("products", []) # get_filtered_contents returns 'products' key
    
    if exclude_ids_key:
        exclude_set = set(exclude_ids_key)
        contents = [c for c in contents if c["id"] not in exclude_set]
        
    return contents[:limit]
