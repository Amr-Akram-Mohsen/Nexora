from app.models import Article, Category, Section, Brand, View, Topic, db
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy import func, case, or_
from datetime import datetime, timedelta

def my_zip(*iterables):
    my_list = []
    for i, val in enumerate(iterables[0]):
        if i == len(iterables[0]) - 1 and i != len(iterables[1]) - 1:
            my_list.append((val, iterables[1][i:]))
        else:
            my_list.append((val, iterables[1][i]))
    return my_list

def get_articles(filter_by_columns: tuple = ('section',), filter_values: tuple = (None,), rows_count=None):
    query = Article.query.options(
        load_only(
            Article.id,
            Article.title,
            Article.url,
            Article.description,
            Article.image_url,
            Article.published_at
        ),
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
                filters.append(Article.sections.any(Section.slug == val))
            elif hasattr(Article, col):
                filters.append(getattr(Article, col) == val)
        if filters:
            query = query.filter(*filters)
    else:
        # eager load sections if not filtering
        query = query.options(joinedload(Article.sections))

    query = query.order_by(Article.published_at.desc())

    if rows_count is not None:
        query = query.limit(rows_count)

    articles = query.all()

    # for a in articles:
    #     a.card_type = 'article'

    return articles


def get_related_articles(article, limit=6):
    topic_ids = [t.id for t in article.topics]
    brand_ids = [b.id for b in article.brands]
    section_ids = [s.id for s in article.sections]

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
        .join(Article.sections)
        .filter(Section.id.in_(section_ids))
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
def get_trending_articles(limit=6, days=7, section_ids=None):
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = (
        db.session.query(
            Article,
            func.count(View.id).label("recent_views")
        )
        .join(View, (View.target_type == "article") & (View.target_id == Article.id))
        .filter(View.created_at >= cutoff)
    )

    if section_ids:
        query = query.join(Article.sections).filter(Section.id.in_(section_ids))

    query = (
        query.group_by(Article.id)
        .order_by(func.count(View.id).desc(), Article.published_at.desc())
        .limit(limit)
    )

    return [row.Article for row in query.all()]

def get_active_brands_for_section(section, limit=5):
    return (
        db.session.query(Brand)
        .join(Brand.articles)
        .join(Article.sections)
        .filter(func.lower(Section.slug) == section)
        .group_by(Brand.id)
        .order_by(func.count(Article.id).desc())
        .limit(limit)
        .all()
    )

def get_active_topics_for_section(section, limit=5):
    return (
        db.session.query(Topic)
        .join(Topic.articles)
        .join(Article.sections)
        .filter(func.lower(Section.slug) == section)
        .group_by(Topic.id)
        .order_by(func.count(Article.id).desc())
        .limit(limit)
        .all()
    )

def get_popular_general_topics():
    return (
        db.session.query(Topic.slug, Topic.name)
        .all()
    )

def get_popular_brands(limit=5):
    return (
        db.session.query(Brand.slug, Brand.name)
        .limit(limit)
        .all()
    )

def get_active_sections():
    return (
        db.session.query(Section.slug, Section.name)
        .filter_by(is_active=1)
        .order_by(Section.sort_order)
        .all()
    )

def get_search_articles(query):
    # Articles: search title/content (limit for speed)
    a_query = Article.query.filter(
        or_(Article.title.ilike(f'%{query}%'), Article.description.ilike(f'%{query}%'))
    )
    return a_query.order_by(Article.published_at.desc()).limit(50).all()
