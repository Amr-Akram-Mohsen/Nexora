from app.infrastructure import cache
from app.domains.content.service import query as domain_query
from app.core.extensions import db

@cache.memoize(timeout=600)
def get_contents_render_cached(filter_by_columns: tuple = ('section',), filter_values: tuple = (None,), rows_count=None):
    return domain_query.get_contents_render(db.session, filter_by_columns, filter_values, rows_count)

@cache.memoize(timeout=3600)
def get_related_contents_cached(content_id, limit=6):
    return domain_query.get_related_contents(db.session, content_id, limit)

@cache.memoize(timeout=300)
def get_trending_contents_cached(limit=6, days=7, section_ids=None):
    return domain_query.get_trending_contents(db.session, limit, days, section_ids)

def get_filtered_contents(section_id, active_filters, allowed_filters, page=1, per_page=24):
    return domain_query.get_filtered_contents(db.session, section_id, active_filters, allowed_filters, page, per_page)
