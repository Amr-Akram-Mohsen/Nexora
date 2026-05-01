from app.core.extensions import db
from ..models import Content
from sqlalchemy import func, case, or_
from datetime import datetime, timedelta, timezone
from app.infrastructure import cache
from sqlalchemy.orm import joinedload, selectinload
from .content_access import assign_target_to_contents
from app.shared.constants.core import TargetType
def my_zip(*iterables):
    my_list = []
    for i, val in enumerate(iterables[0]):
        if i == len(iterables[0]) - 1 and i != len(iterables[1]) - 1:
            my_list.append((val, iterables[1][i:]))
        else:
            my_list.append((val, iterables[1][i]))
    return my_list

@cache.memoize(timeout=600)
def get_contents_render(filter_by_columns: tuple = ('section',), filter_values: tuple = (None,), rows_count=None):
    from app.domains.system.models import Section
    query = Content.query.filter(Content.is_active == True).options(
        selectinload(Content.topics),
        selectinload(Content.brands)
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
        query = query.options(joinedload(Content.section))

    query = query.order_by(Content.published_at.desc())

    if rows_count is not None:
        query = query.limit(rows_count)

    contents = query.all()

    contents = assign_target_to_contents(contents, db.session)

    return contents


@cache.memoize(timeout=3600)
def get_related_contents(content_id, limit=6):
    from ..models import Content
    content = db.session.get(Content, content_id)
    if not content: return []
    from app.domains.system.models import Category, Section, Brand, Topic
    topic_ids = [t.id for t in content.topics]
    brand_ids = [b.id for b in content.brands]
    section_id = content.section_id

    relevance_score = (
        case((Topic.id.in_(topic_ids), 3), else_=0) +
        case((Brand.id.in_(brand_ids), 2), else_=0) +
        case((Category.id.in_([content.category_id]), 1), else_=0)
    )

    query = (
        db.session.query(
            Content,
            func.sum(relevance_score).label("score")
        )
        .join(Content.section)
        .filter(Section.id == section_id)
        .outerjoin(Content.topics)
        .outerjoin(Content.brands)
        .outerjoin(Content.category)
        .filter(Content.id != content.id)
        .group_by(Content.id)
        .having(func.sum(relevance_score) > 0)
        .order_by(
            func.sum(relevance_score).desc(),
            Content.published_at.desc()
        )
        .limit(limit)
    )

    return [row.Content for row in query.all()]

# -------------------------
# Trending Contents
# -------------------------
@cache.memoize(timeout=300)
def get_trending_contents(limit=6, days=7, section_ids=None):
    from app.domains.system.models import Section
    from app.domains.interaction.models import View
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        db.session.query(
            Content,
            func.count(View.id).label("recent_views")
        )
        .join(View, (View.target_type == TargetType.CONTENT) & (View.target_id == Content.id))
        .filter(View.created_at >= cutoff)
    )

    if section_ids:
        query = query.join(Content.section).filter(Section.id.in_(section_ids))

    query = (
        query.group_by(Content.id)
        .order_by(func.count(View.id).desc(), Content.published_at.desc())
        .limit(limit)
    )

    return [row.Content for row in query.all()]

def get_filtered_contents(section, active_filters, allowed_filters, page=1, per_page=24):
    """
    Handles complex filtering and pagination for section contents.
    Uses many-to-one section_id (refactored from many-to-many).
    """
    from app.domains.system.models import Category, Brand, Topic
    query = (
        Content.query
        .filter(Content.section_id == section.id, Content.is_active == True)
        .options(
            db.selectinload(Content.topics),
            db.selectinload(Content.brands)
        )
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

    contents = query.paginate(page=page, per_page=per_page, error_out=False)
    contents.items = assign_target_to_contents(contents.items, db.session)

    return contents

def get_search_contents(query):
    # Contents: search title/content (limit for speed)
    a_query = Content.query.filter(
        or_(Content.title.ilike(f'%{query}%'), Content.description.ilike(f'%{query}%'))
    )
    return a_query.order_by(Content.published_at.desc()).limit(50).all()

def count_contents():
    return db.session.query(Content.id).count()

def get_contents(search=None, source=None, rows_count=10):
    query = Content.query.order_by(Content.published_at.desc())

    if search and search.strip():
        from sqlalchemy import or_
        query = query.filter(or_(Content.title.ilike(f'%{search}%'), Content.description.ilike(f'%{search}%')))

    # source_name column was removed; sources live in the content_sources relationship.
    # Filtering by source slug via the relationship is left for a future enhancement.

    if rows_count:
        query = query.limit(rows_count)

    return query.all()
def get_content_by_id(content_id):
    from app.domains.item.models import Item, ItemVariant, ItemStoreLink
    from app.domains.system.models import Source
    return Content.query.options(
        db.selectinload(Content.topics),
        db.selectinload(Content.brands),
        db.joinedload(Content.section),
        db.joinedload(Content.category),
        db.selectinload(Content.linked_items)
            .selectinload(Item.variants)
            .selectinload(ItemVariant.store_links)
            .selectinload(ItemStoreLink.store),
        db.selectinload(Content.linked_items)
            .selectinload(Item.images),
        db.selectinload(Content.linked_items)
            .selectinload(Item.brand)
    ).get(content_id)

def resolve_content_target(content):
    from .content_access import resolve
    content.target = resolve(content, db.session)
    return content

def get_latest_contents(limit=100):
    return Content.query.order_by(Content.published_at.desc()).limit(limit).all()
