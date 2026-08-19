from app.core.extensions import db
from ...content.models import Content, Article, Event
from ...content.models.author import Author
from app.domains.product.models import Product
from sqlalchemy import func, select, String, cast
from sqlalchemy.orm import selectinload
from app.infrastructure import cache
from datetime import datetime, timedelta, timezone
from app.domains.relationships import ContentEntity, article_authors, content_locations, content_attributes, content_products
from ..models import Category, Brand, Entity, IntentFacet, PriceTierFacet, Section, AttributeFacet, Source, Location
REL_MODELS = {'category': Category, 'brand': Brand, 'entity': Entity, 'intent': IntentFacet, 'price_tier': PriceTierFacet, 'attributes': AttributeFacet}

def build_filter_projection(model):
    slug_col = model.slug if hasattr(model, 'slug') else cast(model.id, String)
    name_col = model.name if hasattr(model, 'name') else model.title if hasattr(model, 'title') else cast(model.id, String)
    return (slug_col.label('slug'), name_col.label('name'))

def apply_content_section_filters(stmt, model, section_slug, limit=20, min_count=None):
    stmt = stmt.where(Content.is_active, Content.is_published)
    if section_slug and section_slug != 'all':
        stmt = stmt.join(Section, Section.id == Content.section_id).where(func.lower(Section.slug) == func.lower(section_slug))
    group_cols = [model.id]
    if hasattr(model, 'slug'):
        group_cols.append(model.slug)
    if hasattr(model, 'name'):
        group_cols.append(model.name)
    elif hasattr(model, 'title'):
        group_cols.append(model.title)
    stmt = stmt.group_by(*group_cols)
    if min_count:
        stmt = stmt.having(func.count(Content.id) >= min_count)
    return stmt.order_by(func.count(Content.id).desc()).limit(limit)

def execute_mapped_query(stmt, session=None):
    session = session or db.session
    rows = session.execute(stmt).mappings().all()
    return [dict(row) for row in rows]

def get_taxonomy_mappings(model_class, used_in_model=None, used_in_column=None, session=None):
    session = session or db.session
    stmt = select(model_class.id, model_class.name, model_class.slug)
    if used_in_model is not None and used_in_column is not None:
        stmt = stmt.where(model_class.id.in_(select(used_in_column).distinct()))
    rows = session.execute(stmt.order_by(model_class.name)).mappings().all()
    return [dict(r) for r in rows]

def get_taxonomy_content_stats(entity_id, field=None, relationship_table=None, foreign_key_col=None, session=None):
    session = session or db.session
    breakdown_stmt = select(Content.object_type, func.count(Content.id))
    eng_stmt = select(func.sum(Content.view_count), func.sum(Content.like_count), func.sum(Content.share_count))
    top_stmt = select(Content).order_by(Content.view_count.desc()).limit(5)
    if relationship_table is not None and foreign_key_col is not None:
        breakdown_stmt = breakdown_stmt.join(relationship_table, relationship_table.c.content_id == Content.id).where(foreign_key_col == entity_id).group_by(Content.object_type)
        eng_stmt = eng_stmt.join(relationship_table, relationship_table.c.content_id == Content.id).where(foreign_key_col == entity_id)
        top_stmt = top_stmt.join(relationship_table, relationship_table.c.content_id == Content.id).where(foreign_key_col == entity_id)
    elif field is not None:
        breakdown_stmt = breakdown_stmt.where(field == entity_id).group_by(Content.object_type)
        eng_stmt = eng_stmt.where(field == entity_id)
        top_stmt = top_stmt.where(field == entity_id)
    else:
        raise ValueError('Must provide either a field or a relationship_table/foreign_key_col pair.')
    type_breakdown = session.execute(breakdown_stmt).all()
    engagement = session.execute(eng_stmt).first()
    top_contents = session.execute(top_stmt).scalars().all()
    return (type_breakdown, engagement, top_contents)

@cache.memoize(timeout=3600)
def get_relationships_for_section(section_slug, rel_name, limit=20, session=None):
    session = session or db.session
    rel_model = REL_MODELS.get(rel_name, None)
    match rel_name:
        case 'category' | 'intent' | 'price_tier' | 'attributes':
            stmt = select(*build_filter_projection(rel_model)).join(rel_model.contents)
        case 'entity' | 'brand' | 'topic' | 'tag':
            stmt = select(*build_filter_projection(rel_model)).join(ContentEntity, ContentEntity.entity_id == Entity.id).join(Content, Content.id == ContentEntity.content_id)
            if rel_name == 'brand':
                stmt = stmt.where(Entity.entity_type == 'brand')
            elif rel_name in ('topic', 'tag'):
                stmt = stmt.where(Entity.entity_type.in_(['topic', 'tag', 'concept']))
        # case 'brand':
        #     rel_model = Entity
        #     stmt = select(*build_filter_projection(rel_model)).join(ContentEntity, ContentEntity.entity_id == Entity.id).join(Content, Content.id == ContentEntity.content_id).where(Entity.entity_type == 'brand')
        # case 'topic' | 'tag':
        #     rel_model = Entity
        #     stmt = select(*build_filter_projection(rel_model)).join(ContentEntity, ContentEntity.entity_id == Entity.id).join(Content, Content.id == ContentEntity.content_id).where(Entity.entity_type.in_(['topic', 'tag', 'concept']))
        case 'source':
            rel_model = Source
            stmt = select(*build_filter_projection(rel_model)).join(Content, Content.source_id == Source.id)
        case 'author':
            rel_model = Author
            stmt = select(*build_filter_projection(rel_model)).join(article_authors, article_authors.c.author_id == Author.id).join(Article, Article.id == article_authors.c.article_id).join(Content, (Content.object_id == Article.id) & (Content.object_type == 'article'))
        case 'event':
            rel_model = Event
            stmt = select(*build_filter_projection(rel_model)).join(Article, Article.event_id == Event.id).join(Content, (Content.object_id == Article.id) & (Content.object_type == 'article'))
        case 'location':
            rel_model = Location
            stmt = select(*build_filter_projection(rel_model)).join(content_locations, content_locations.c.location_id == Location.id).join(Content, Content.id == content_locations.c.content_id)
        case _:
            raise ValueError('Invalid relationship name')
    min_count_map = {'category': 5, 'entity': 5, 'brand': 5, 'topic': 5, 'tag': 5, 'author': 3, 'source': 3}
    min_count = min_count_map.get(rel_name, 1)
    stmt = apply_content_section_filters(stmt=stmt, model=rel_model, section_slug=section_slug, limit=limit, min_count=min_count)
    return execute_mapped_query(stmt, session)

@cache.memoize(timeout=3600)
def get_types_for_section(section_slug, session=None):
    stmt = select(Content.object_type)
    if section_slug and section_slug != 'all':
        stmt = stmt.join(Section, Section.id == Content.section_id).where(func.lower(Section.slug) == func.lower(section_slug))
    stmt = stmt.group_by(Content.object_type)
    rows = execute_mapped_query(stmt, session)
    return [{'slug': r['object_type'].lower(), 'name': r['object_type'].title()} for r in rows if r.get('object_type')]

@cache.memoize(timeout=3600)
def get_popular_general_topics(limit=4, session=None):
    stmt = select(*build_filter_projection(Entity)).where(Entity.entity_type.in_(['topic', 'concept', 'tag'])).limit(limit)
    return execute_mapped_query(stmt, session)

@cache.memoize(timeout=3600)
def get_popular_brands(limit=5, session=None):
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    stmt = select(*build_filter_projection(Entity), func.sum(Content.view_count).label('recent_views')).join(ContentEntity, Entity.id == ContentEntity.entity_id).join(Content, Content.id == ContentEntity.content_id).where((Entity.entity_type == 'brand') | (Entity.entity_type == 'organization'), Content.is_active.is_(True), Content.is_published.is_(True), Content.published_at >= cutoff).group_by(Entity.id, Entity.slug, Entity.name).order_by(func.sum(Content.view_count).desc()).limit(limit)
    return execute_mapped_query(stmt, session)

@cache.memoize(timeout=3600)
def get_active_sections(session=None):
    stmt = select(*build_filter_projection(Section)).where(Section.is_active)
    return execute_mapped_query(stmt, session)

def get_section_by_slug(slug, session=None):
    session = session or db.session
    stmt = select(Section).where(Section.slug == slug, Section.is_active)
    return session.execute(stmt).scalars().first()

@cache.memoize(timeout=1800)
def get_trending_brands(limit: int=6, days: int=7, session=None):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(*build_filter_projection(Entity), func.sum(Content.view_count).label('recent_views')).join(ContentEntity, Entity.id == ContentEntity.entity_id).join(Content, Content.id == ContentEntity.content_id).where((Entity.entity_type == 'brand') | (Entity.entity_type == 'organization'), Content.is_active.is_(True), Content.is_published.is_(True), Content.published_at >= cutoff).group_by(Entity.id, Entity.slug, Entity.name).order_by(func.sum(Content.view_count).desc()).limit(limit)
    return execute_mapped_query(stmt, session)

def _get_distinct_item_taxonomy(model_class, session=None):
    stmt = select(model_class.slug, model_class.name).join(Product).distinct().order_by(model_class.name)
    return execute_mapped_query(stmt, session)

@cache.memoize(timeout=3600)
def get_distinct_item_categories(session=None):
    return _get_distinct_item_taxonomy(Category, session)

@cache.memoize(timeout=3600)
def get_distinct_item_brands(session=None):
    return _get_distinct_item_taxonomy(Brand, session)

def get_attributes_for_section(section_slug, category_slugs=None, limit=20, session=None):
    if category_slugs:
        if isinstance(category_slugs, str):
            category_slugs = (category_slugs,)
        elif isinstance(category_slugs, list):
            category_slugs = tuple(sorted([s for s in category_slugs if s]))
    else:
        category_slugs = None
    return get_cached_attributes_for_section(section_slug, category_slugs, limit, session)

@cache.memoize(timeout=3600)
def get_cached_attributes_for_section(section_slug, category_slugs_tuple, limit, session=None):
    stmt = select(*build_filter_projection(AttributeFacet)).join(AttributeFacet.contents)
    if category_slugs_tuple:
        session = session or db.session
        categories = session.execute(select(Category).options(selectinload(Category.children)).where(func.lower(Category.slug).in_([func.lower(s) for s in category_slugs_tuple]))).scalars().all()
        category_ids = set()
        for cat in categories:
            category_ids.add(cat.id)
            if cat.parent_id:
                category_ids.add(cat.parent_id)
            if cat.children:
                for child in cat.children:
                    category_ids.add(child.id)
        stmt = stmt.where(AttributeFacet.category_id.in_(list(category_ids)))
    stmt = apply_content_section_filters(stmt=stmt, model=AttributeFacet, section_slug=section_slug, limit=limit)
    return execute_mapped_query(stmt, session)


_cached_attributes_for_section = get_cached_attributes_for_section


def paginate_taxonomy_entity(model, page, per_page, search='', status=None, health=None, field_name=None, extra_filter=None):
    stmt = select(model).order_by(model.name.asc())
    if extra_filter is not None:
        stmt = stmt.where(extra_filter)
    if search:
        stmt = stmt.where(model.name.ilike(f'%{search}%'))
    if hasattr(model, 'is_active'):
        if status == '1':
            stmt = stmt.where(model.is_active == True)
        elif status == '0':
            stmt = stmt.where(model.is_active == False)
    if health:
        cond_content = None
        cond_item = None
        if model == Category:
            cond_content = db.session.query(Content.id).filter(Content.category_id == Category.id).exists()
            cond_item = db.session.query(Product.id).filter(Product.category_id == Category.id).exists()
        elif model == Brand:
            cond_item = db.session.query(Product.id).filter(Product.brand_id == Brand.id).exists()
        elif model == Entity:
            cond_content = db.session.query(ContentEntity.content_id).filter(ContentEntity.entity_id == Entity.id).exists()
        elif model == Section:
            cond_content = db.session.query(Content.id).filter(Content.section_id == Section.id).exists()
        elif model == AttributeFacet:
            cond_content = db.session.query(content_attributes.c.content_id).filter(content_attributes.c.attribute_id == AttributeFacet.id).exists()
        elif field_name:
            field = getattr(Content, field_name)
            cond_content = db.session.query(Content.id).filter(field == model.id).exists()
        if health == 'unused':
            if cond_content is not None:
                stmt = stmt.where(~cond_content)
            if cond_item is not None:
                stmt = stmt.where(~cond_item)
        elif health == 'inactive-linked' and hasattr(model, 'is_active'):
            stmt = stmt.where(model.is_active == False)
            if cond_content is not None and cond_item is not None:
                stmt = stmt.where(cond_content | cond_item)
            elif cond_content is not None:
                stmt = stmt.where(cond_content)
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

@cache.memoize(timeout=3600)
def get_taxonomy_filters(section_slug, allowed_filters_tuple, category_slugs_tuple=None):
    filter_options = {}
    relationship_filters = ['category', 'entity', 'intent', 'price_tier', 'source', 'event', 'location', 'author']
    for f in relationship_filters:
        if f in allowed_filters_tuple:
            filter_options[f] = get_relationships_for_section(section_slug, f)
    if 'type' in allowed_filters_tuple:
        filter_options['type'] = get_types_for_section(section_slug)
    if 'attributes' in allowed_filters_tuple:
        filter_options['attributes'] = get_attributes_for_section(section_slug, category_slugs=category_slugs_tuple)
    return filter_options