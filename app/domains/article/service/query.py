from app.core.extensions import db
from ..models import Article
# from app.domains.system.models import Category, Section, Brand, Topic
# from app.domains.interaction.models import View
from sqlalchemy import func, case, or_
from datetime import datetime, timedelta, timezone
from app.core.extensions import cache
from sqlalchemy.orm import joinedload, selectinload, defer

def my_zip(*iterables):
    my_list = []
    for i, val in enumerate(iterables[0]):
        if i == len(iterables[0]) - 1 and i != len(iterables[1]) - 1:
            my_list.append((val, iterables[1][i:]))
        else:
            my_list.append((val, iterables[1][i]))
    return my_list

def get_articles_render(filter_by_columns: tuple = ('section',), filter_values: tuple = (None,), rows_count=None):
    from app.domains.system.models import Section
    query = Article.query.filter(Article.is_active == True).options(
        defer(Article.content),
        selectinload(Article.topics),
        selectinload(Article.brands)
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
                filters.append(Article.section.has(Section.slug == val))
            elif hasattr(Article, col):
                filters.append(getattr(Article, col) == val)
        if filters:
            query = query.filter(*filters)
    else:
        # eager load section if not filtering
        query = query.options(joinedload(Article.section))

    query = query.order_by(Article.published_at.desc())

    if rows_count is not None:
        query = query.limit(rows_count)

    articles = query.all()

    # for a in articles:
    #     a.card_type = 'article'

    return articles


def get_related_articles(article, limit=6):
    from app.domains.system.models import Category, Section, Brand, Topic
    topic_ids = [t.id for t in article.topics]
    brand_ids = [b.id for b in article.brands]
    section_id = article.section_id

    relevance_score = (
        case((Topic.id.in_(topic_ids), 3), else_=0) +
        case((Brand.id.in_(brand_ids), 2), else_=0) +
        case((Category.id.in_([article.category_id]), 1), else_=0)
    )

    query = (
        db.session.query(
            Article,
            func.sum(relevance_score).label("score")
        )
        .join(Article.section)
        .filter(Section.id == section_id)
        .outerjoin(Article.topics)
        .outerjoin(Article.brands)
        .outerjoin(Article.category)
        .filter(Article.id != article.id)
        .group_by(Article.id)
        .having(func.sum(relevance_score) > 0)
        .order_by(
            func.sum(relevance_score).desc(),
            Article.published_at.desc()
        )
        .limit(limit)
    )

    return [row.Article for row in query.all()]

# -------------------------
# Trending Articles
# -------------------------
@cache.memoize(timeout=300)
def get_trending_articles(limit=6, days=7, section_ids=None):
    from app.domains.system.models import Section
    from app.domains.interaction.models import View
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        db.session.query(
            Article,
            func.count(View.id).label("recent_views")
        )
        .join(View, (View.target_type == "article") & (View.target_id == Article.id))
        .filter(View.created_at >= cutoff)
    )

    if section_ids:
        query = query.join(Article.section).filter(Section.id.in_(section_ids))

    query = (
        query.group_by(Article.id)
        .order_by(func.count(View.id).desc(), Article.published_at.desc())
        .limit(limit)
    )

    return [row.Article for row in query.all()]

def get_filtered_articles(section, active_filters, allowed_filters, page=1, per_page=24):
    """
    Handles complex filtering and pagination for section articles.
    Uses many-to-one section_id (refactored from many-to-many).
    """
    from app.domains.system.models import Category, Brand, Topic
    query = (
        Article.query
        .filter(Article.section_id == section.id, Article.is_active == True)
        .options(
            db.defer(Article.content),
            db.selectinload(Article.topics),
            db.selectinload(Article.brands)
        )
    )

    if active_filters.get('category'):
        query = query.join(Article.category).filter(Category.slug.in_(active_filters['category']))
    
    if active_filters.get('topic') and "topic" in allowed_filters:
        query = query.join(Article.topics).filter(Topic.slug.in_(active_filters['topic']))
    
    if active_filters.get('brand') and "brand" in allowed_filters:
        query = query.join(Article.brands).filter(Brand.slug.in_(active_filters['brand']))

    if active_filters.get('sort') == 'oldest':
        query = query.order_by(Article.published_at.asc())
    else:
        query = query.order_by(Article.published_at.desc())

    return query.distinct().paginate(page=page, per_page=per_page, error_out=False)

def get_search_articles(query):
    # Articles: search title/content (limit for speed)
    a_query = Article.query.filter(
        or_(Article.title.ilike(f'%{query}%'), Article.description.ilike(f'%{query}%'))
    )
    return a_query.order_by(Article.published_at.desc()).limit(50).all()

def count_articles():
    return db.session.query(Article.id).count()

def get_articles(search=None, source=None, rows_count=10):
    query = Article.query.order_by(Article.published_at.desc())

    if search and search.strip():
        from sqlalchemy import or_
        query = query.filter(or_(Article.title.ilike(f'%{search}%'), Article.description.ilike(f'%{search}%')))

    # source_name column was removed; sources live in the article_sources relationship.
    # Filtering by source slug via the relationship is left for a future enhancement.

    if rows_count:
        query = query.limit(rows_count)

    return query.all()
