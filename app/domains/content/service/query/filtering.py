from ...models import Content
from ..content_access import assign_target_to_contents
from app.shared.utils.collections import my_zip

def get_contents_render(session, filter_by_columns: tuple = ('section',), filter_values: tuple = (None,), rows_count=None):
    from .options import CONTENT_EAGER_LOADS
    from app.domains.system.models import Section
    query = session.query(Content).filter(Content.is_active == True).options(
        *CONTENT_EAGER_LOADS
    )

    if filter_by_columns and filter_values:
        filter_dict = None
        if len(filter_by_columns) != len(filter_values):
            filter_dict = dict(my_zip(filter_by_columns, filter_values))
        else:
            filter_dict = dict(zip(filter_by_columns, filter_values))
        filters = []
        for col, val in filter_dict.items():
            if col == 'section':
                filters.append(Content.section.has(Section.slug == val))
            elif hasattr(Content, col):
                filters.append(getattr(Content, col) == val)
        if filters:
            query = query.filter(*filters)
    else:
        # eager load section if not filtering
        pass

    query = query.order_by(Content.published_at.desc())

    if rows_count is not None:
        query = query.limit(rows_count)

    contents = query.all()

    contents = assign_target_to_contents(contents, session)

    return contents


def get_filtered_contents(session, section_id, active_filters, allowed_filters, page=1, per_page=24):
    """
    Handles complex filtering and pagination for section contents.
    """
    from app.domains.system.models import Category, Brand, Topic
    from .options import CONTENT_EAGER_LOADS
    query = (
        session.query(Content)
        .filter(Content.section_id == section_id, Content.is_active == True)
        .options(*CONTENT_EAGER_LOADS)
    )

    cats = [f for f in active_filters.get('category', []) if f]
    if cats and "category" in allowed_filters:
        query = query.filter(Content.category.has(Category.slug.in_(cats)))
    
    topics = [f for f in active_filters.get('topic', []) if f]
    if topics and "topic" in allowed_filters:
        query = query.filter(Content.topics.any(Topic.slug.in_(topics)))
    
    brands = [f for f in active_filters.get('brand', []) if f]
    if brands and "brand" in allowed_filters:
        query = query.filter(Content.brands.any(Brand.slug.in_(brands)))

    if active_filters.get('sort') == 'oldest':
        query = query.order_by(Content.published_at.asc())
    else:
        query = query.order_by(Content.published_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination.items = assign_target_to_contents(pagination.items, session)

    return pagination
