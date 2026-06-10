from sqlalchemy import select, or_
from app.domains.content.models import Content

def get_content_eager_loads(mode="default"):
    """
    Retrieves eager-loading options based on the specified mode/profile.
    - 'detail': Eager loading for detail views (including linked items, variants, etc.)
    - 'list': Eager loading for list views (topics, brands, joined section/category)
    - 'default': Default eager loading (topics, brands, section, category via selectinload)
    - None or 'none': No eager loading
    - If a list or tuple of options is passed, it is used directly (override).
    """
    from .options import CONTENT_EAGER_LOADS, CONTENT_LIST_EAGER_LOADS, get_content_detail_loads
    
    if mode is None or mode == "none":
        return []
    if isinstance(mode, (list, tuple)):
        return list(mode)
    if mode == "list":
        return CONTENT_LIST_EAGER_LOADS
    if mode == "detail":
        return get_content_detail_loads()
    if mode == "default":
        return CONTENT_EAGER_LOADS
    return CONTENT_EAGER_LOADS

def build_content_stmt(active_only=True, published_only=True, eager_load="default"):
    """
    Constructs a base SQLAlchemy 2.0 select statement for the Content model.
    """
    stmt = select(Content)
    
    if active_only:
        stmt = stmt.where(Content.is_active == True)
    if published_only:
        stmt = stmt.where(Content.is_published == True)
        
    loads = get_content_eager_loads(eager_load)
    if loads:
        stmt = stmt.options(*loads)
        
    return stmt

def build_ranked_content_stmt(stmt, rank_expr, label_name="score"):
    """
    Appends ranking/aggregation expressions and grouping/ordering to a select statement.
    """
    stmt = stmt.add_columns(rank_expr.label(label_name))
    stmt = stmt.group_by(Content.id)
    stmt = stmt.order_by(rank_expr.desc(), Content.published_at.desc())
    return stmt

def apply_column_filters(stmt, filter_by_columns, filter_values):
    """
    Applies column equality filters and section slug filtering on Content statement.
    """
    from app.shared.utils.collections import my_zip
    from app.domains.taxonomy.models import Section
    
    if not (filter_by_columns and filter_values):
        return stmt
        
    if len(filter_by_columns) != len(filter_values):
        filter_dict = dict(my_zip(filter_by_columns, filter_values))
    else:
        filter_dict = dict(zip(filter_by_columns, filter_values))
        
    filters = []
    for col, val in filter_dict.items():
        if col == "section":
            filters.append(Content.section.has(Section.slug == val))
        elif hasattr(Content, col):
            filters.append(getattr(Content, col) == val)
            
    if filters:
        stmt = stmt.where(*filters)
        
    return stmt

def fetch_contents(stmt, session=None):
    """
    Executes a select statement and extracts Content entities from the results.
    """
    if session is None:
        from app.core.extensions import db
        session = db.session
        
    result = session.execute(stmt)
    rows = result.all()
    if not rows:
        return []
        
    # Extract the Content entity (first element in each row tuple)
    return [row[0] for row in rows]

def fetch_serialized_contents(stmt, session=None, include_linked_items=False):
    """
    Executes a select statement, extracts Content entities, and serializes them.
    """
    if session is None:
        from app.core.extensions import db
        session = db.session
        
    contents = fetch_contents(stmt, session)
    from ..content_access import assign_target_to_contents
    return assign_target_to_contents(contents, session, include_linked_items=include_linked_items)
