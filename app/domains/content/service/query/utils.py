from sqlalchemy import select, or_
from app.domains.content.models import Content

def get_content_eager_loads(mode="default"):
    """
    Retrieves eager-loading options based on the specified mode/profile.
    - 'detail': Eager loading for detail views (including linked products, variants, etc.)
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
    from app.domains.taxonomy.models import Category, Brand, Entity, IntentFacet, PriceTierFacet, AttributeFacet, Section, Source, GenderFacet
    from app.domains.relationships import ContentEntity
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

    entities = _normalize(filters.get("entity"))
    if entities and _is_allowed("entity"):
        if "none" in entities:
            stmt = stmt.where(~Content.content_entities.any())
        else:
            stmt = stmt.where(Content.content_entities.any(ContentEntity.entity.has(Entity.slug.in_(entities))))

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

    events = _normalize(filters.get("event"))
    if events and _is_allowed("event"):
        from app.domains.content.models import Article, Event
        stmt = stmt.where(
            Content.object_type == "article",
            Content.object_id.in_(
                select(Article.id).where(Article.event.has(Event.external_uri.in_(events)))
            )
        )

    locations = _normalize(filters.get("location"))
    if locations and _is_allowed("location"):
        from app.domains.taxonomy.models import Location
        stmt = stmt.where(Content.locations.any(Location.slug.in_(locations)))

    authors = _normalize(filters.get("author"))
    if authors and _is_allowed("author"):
        # For Article, authors is a JSON array of strings
        from app.domains.content.models import Article
        from sqlalchemy import cast, String
        from sqlalchemy.dialects.postgresql import JSONB
        author_filters = []
        for a in authors:
            author_filters.append(cast(Article.authors, String).ilike(f"%{a}%"))
        
        stmt = stmt.where(
            Content.object_type == "article",
            Content.object_id.in_(
                select(Article.id).where(or_(*author_filters))
            )
        )

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

