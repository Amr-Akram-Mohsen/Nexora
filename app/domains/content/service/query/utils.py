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
    
    # Additional condition for testing article markdown content
    from app.domains.content.models import Article
    stmt = stmt.outerjoin(Article, (Content.object_id == Article.id) & (Content.object_type == 'article'))
    stmt = stmt.where(
        or_(
            Content.object_type != 'article',
            Article.content_markdown.is_not(None)
        )
    )
        
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
        
    return list(session.execute(stmt).scalars().all())

def fetch_serialized_contents(stmt, session=None, include_linked_items=False):
    """
    Executes a select statement, extracts Content entities, and serializes them.
    """
    if session is None:
        from app.core.extensions import db
        session = db.session
        
    contents = fetch_contents(stmt, session)
    from ..content_access import assign_target_to_contents
    return assign_target_to_contents(contents, include_linked_items=include_linked_items, session=session)


def apply_content_filters(stmt, filters, allowed_filters=None, session=None):
    """
    Applies unified content filters across public and admin interfaces.
    """
    from sqlalchemy import select, or_
    from app.domains.taxonomy.models import Category, Brand, Topic, IntentFacet, PriceTierFacet, AttributeFacet, Section, Source, GenderFacet
    from app.domains.content.models import Content
    
    if session is None:
        from app.core.extensions import db
        session = db.session

    def _is_allowed(key):
        return allowed_filters is None or key in allowed_filters

    def _normalize(val):
        if not val: return []
        if isinstance(val, str):
            if val.lower() == "none": return ["none"]
            return [val]
        return [f for f in val if f]

    cats = _normalize(filters.get("category"))
    if cats and _is_allowed("category"):
        if "uncategorized" in cats:
             stmt = stmt.where(or_(Content.category_id.is_(None), Content.category.has(Category.slug == "uncategorized")))
        else:
            from sqlalchemy.orm import selectinload
            category_objs = session.execute(
                select(Category).options(selectinload(Category.children)).where(Category.slug.in_(cats))
            ).scalars().all()
            
            cat_ids = set()
            for cat in category_objs:
                cat_ids.add(cat.id)
                if cat.children:
                    for child in cat.children:
                        cat_ids.add(child.id)
            if cat_ids:
                stmt = stmt.where(Content.category_id.in_(list(cat_ids)))

    topics = _normalize(filters.get("topic"))
    if topics and _is_allowed("topic"):
        if "none" in topics:
            stmt = stmt.where(~Content.topics.any())
        else:
            stmt = stmt.where(Content.topics.any(Topic.slug.in_(topics)))

    brands = _normalize(filters.get("brand"))
    if brands and _is_allowed("brand"):
        if "none" in brands:
            stmt = stmt.where(~Content.brands.any())
        else:
            stmt = stmt.where(Content.brands.any(Brand.slug.in_(brands)))

    intents = _normalize(filters.get("intent"))
    if intents and _is_allowed("intent"):
        stmt = stmt.where(Content.intent.has(IntentFacet.slug.in_(intents)))

    genders = _normalize(filters.get("gender"))
    if genders and _is_allowed("gender"):
        stmt = stmt.where(Content.gender.has(GenderFacet.slug.in_(genders)))

    price_tiers = _normalize(filters.get("price_tier"))
    if price_tiers and _is_allowed("price_tier"):
        stmt = stmt.where(Content.price_tier.has(PriceTierFacet.slug.in_(price_tiers)))

    attributes = _normalize(filters.get("attributes"))
    if attributes and _is_allowed("attributes"):
        stmt = stmt.where(Content.attributes.any(AttributeFacet.slug.in_(attributes)))

    types = _normalize(filters.get("type"))
    if types and _is_allowed("type"):
        stmt = stmt.where(Content.object_type.in_(types))

    sections = _normalize(filters.get("section"))
    if sections and _is_allowed("section"):
        stmt = stmt.where(Content.section.has(Section.slug.in_(sections)))

    sources = _normalize(filters.get("source"))
    if sources and _is_allowed("source"):
        stmt = stmt.where(Content.source.has(Source.slug.in_(sources)))

    search = filters.get("search")
    if search and search.strip() and _is_allowed("search"):
        term = f"%{search.strip()}%"
        if search.strip().isdigit():
            stmt = stmt.where(or_(Content.id == int(search.strip()), Content.title.ilike(term)))
        else:
            stmt = stmt.where(or_(Content.title.ilike(term), Content.preview_text.ilike(term)))

    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    date_type = filters.get("date_type", "published_at")
    if (start_date or end_date) and _is_allowed("date"):
        from datetime import datetime
        date_col = Content.published_at if date_type == "published_at" else Content.ingested_at
        if start_date:
            try:
                stmt = stmt.where(date_col >= datetime.strptime(start_date, "%Y-%m-%d"))
            except ValueError:
                pass
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                stmt = stmt.where(date_col <= end_dt)
            except ValueError:
                pass

    status = filters.get("status")
    if status and _is_allowed("status"):
        from app.domains.content.models import Article
        stmt = stmt.where(Content.object_type == "article", Content.object_id.in_(select(Article.id).where(Article.status == status)))
        
    origin = filters.get("ingestion_origin")
    if origin and _is_allowed("ingestion_origin"):
        stmt = stmt.where(Content.ingestion_origin == origin)
        
    return stmt

