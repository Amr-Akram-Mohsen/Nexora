from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, timezone, timedelta
from app.core.extensions import db
from app.domains.content.models import Content, Article, Video, Post
from app.domains.taxonomy.models import Category, Section, Source, IntentFacet, GenderFacet, PriceTierFacet
from app.domains.interaction.models import Comment, Reaction, View
from app.domains.relationships import ArticleSource

def load_admin_content_relations(page_items, quality):
    ids_by_type: dict[str, set] = {}
    for c in page_items:
        ids_by_type.setdefault(c.object_type, set()).add(c.object_id)
    targets_map = {}
    for obj_type, ids in ids_by_type.items():
        model = {'article': Article, 'video': Video, 'post': Post}.get(obj_type)
        if model:
            stmt = select(model).where(model.id.in_(list(ids)))
            if model == Article:
                stmt = stmt.options(selectinload(Article.article_sources).joinedload(ArticleSource.source))
            objs = db.session.execute(stmt).scalars().all()
            for obj in objs:
                targets_map[obj_type, obj.id] = obj
    duplicate_titles: set = set()
    if quality == 'duplicate':
        titles = [c.title for c in page_items if c.title]
        if titles:
            dup_rows = db.session.execute(select(Content.title).where(Content.title.in_(titles)).group_by(Content.title).having(func.count(Content.id) > 1)).scalars().all()
            duplicate_titles = set(dup_rows)
    return (targets_map, duplicate_titles)

def get_admin_content_metadata():
    from app.domains.taxonomy.service.query import get_taxonomy_mappings
    categories = get_taxonomy_mappings(Category)
    sections = get_taxonomy_mappings(Section)
    sources = get_taxonomy_mappings(Source)
    topics = []
    brands = []
    intents = get_taxonomy_mappings(IntentFacet)
    genders = get_taxonomy_mappings(GenderFacet)
    price_tiers = get_taxonomy_mappings(PriceTierFacet)
    origins_rows = db.session.execute(select(Content.ingestion_origin).filter(Content.ingestion_origin.is_not(None)).distinct()).scalars().all()
    return {'categories': categories, 'sections': sections, 'sources': sources, 'topics': topics, 'brands': brands, 'intents': intents, 'genders': genders, 'price_tiers': price_tiers, 'origins': [{'slug': o, 'name': o} for o in origins_rows]}

def get_admin_content_stats():
    total = db.session.query(func.count(Content.id)).scalar()
    published = db.session.query(func.count(Content.id)).filter(Content.is_published == True).scalar()
    drafts = total - published
    failed = db.session.query(func.count(Article.id)).filter(Article.status == 'failed').scalar()
    no_topics = 0
    no_brands = 0
    return {'total': total, 'published': published, 'drafts': drafts, 'failed': failed, 'no_topics': no_topics, 'no_brands': no_brands}

def retry_admin_pipeline(origin):
    query = db.session.query(Article).join(Content, Content.object_id == Article.id).filter(Content.object_type == 'article', Article.status == 'failed')
    if origin:
        query = query.filter(Content.ingestion_origin == origin)
    articles_to_retry = query.all()
    for a in articles_to_retry:
        a.status = 'pending'
    return len(articles_to_retry)

def get_admin_deduplication_groups():
    from collections import defaultdict
    dup_titles_rows = db.session.execute(
        select(Content.title, func.count(Content.id))
        .where(Content.title.is_not(None), Content.title != '')
        .group_by(Content.title)
        .having(func.count(Content.id) > 1)
        .order_by(func.count(Content.id).desc())
        .limit(20)
    ).all()

    if not dup_titles_rows:
        return []

    title_counts = {title: count for title, count in dup_titles_rows if title}
    titles_list = list(title_counts.keys())

    contents = db.session.execute(
        select(Content)
        .options(joinedload(Content.source))
        .where(Content.title.in_(titles_list))
    ).scalars().all()

    items_by_title = defaultdict(list)
    for i in contents:
        items_by_title[i.title].append({
            'id': i.id,
            'type': i.object_type,
            'published_at': i.published_at.isoformat() if i.published_at else None,
            'source': i.source.name if i.source else 'None'
        })

    groups = []
    for title in titles_list:
        groups.append({
            'title': title,
            'count': title_counts[title],
            'content_list': items_by_title.get(title, [])
        })
    return groups

def get_admin_content_inspect_raw(id):
    content = db.session.scalar(select(Content).options(joinedload(Content.category), joinedload(Content.section), joinedload(Content.source), joinedload(Content.gender), joinedload(Content.intent), joinedload(Content.price_tier), selectinload(Content.content_entities), selectinload(Content.linked_products), selectinload(Content.comments).joinedload(Comment.user)).where(Content.id == id))
    if not content:
        return None
    target = None
    if content.object_type in ('article', 'video', 'post'):
        model = {'article': Article, 'video': Video, 'post': Post}.get(content.object_type)
        if model:
            stmt = select(model).where(model.id == content.object_id)
            if model == Article:
                stmt = stmt.options(selectinload(Article.article_sources).joinedload(ArticleSource.source))
            target = db.session.scalar(stmt)
    return {'content': content, 'target': target}