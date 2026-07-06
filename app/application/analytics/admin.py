from app.infrastructure import cache
from app.domains.analytics.service.admin import (
    get_admin_dashboard_stats_data as _get_admin_dashboard_stats_data,
    get_admin_top_contents as _get_admin_top_contents,
    get_admin_top_items as _get_admin_top_items,
    get_admin_content_dashboard_stats as _get_admin_content_dashboard_stats,
    get_admin_pipeline_stats as _get_admin_pipeline_stats
)

@cache.memoize(timeout=300)
def get_admin_dashboard_stats_data():
    return _get_admin_dashboard_stats_data()

@cache.memoize(timeout=300)
def get_admin_top_contents():
    return _get_admin_top_contents()

@cache.memoize(timeout=300)
def get_admin_top_items():
    return _get_admin_top_items()

@cache.memoize(timeout=300)
def get_admin_content_dashboard_stats():
    return _get_admin_content_dashboard_stats()

@cache.memoize(timeout=300)
def get_admin_pipeline_stats():
    return _get_admin_pipeline_stats()
