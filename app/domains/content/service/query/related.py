from sqlalchemy import case, func, literal_column, cast, Float, select
from app.core.extensions import db
from ...models import Content
from app.domains.content.models.article import Article
from app.domains.taxonomy.models import Entity
from app.domains.relationships import ContentEntity
from .utils import build_content_stmt, build_ranked_content_stmt, fetch_serialized_contents

def get_related_contents(content_id, limit=6, session=None):
    session = session or db.session
    ref_stmt = build_content_stmt(active_only=False, published_only=False, eager_load='default').where(Content.id == content_id)
    reference = session.execute(ref_stmt).scalars().first()
    if not reference:
        return []
    topic_entity_ids = []
    brand_entity_ids = []
    for ce in reference.content_entities:
        if ce.entity:
            if ce.entity.entity_type in ('tag', 'concept', 'topic'):
                topic_entity_ids.append(ce.entity_id)
            elif ce.entity.entity_type == 'brand' or ce.origin == 'legacy_brand':
                brand_entity_ids.append(ce.entity_id)
    category_id = reference.category_id
    section_id = reference.section_id
    event_id = None
    if reference.object_type == 'article':
        article_obj = session.get(Article, reference.object_id)
        if article_obj:
            event_id = article_obj.event_id
    if topic_entity_ids:
        topic_score = case((ContentEntity.entity_id.in_(topic_entity_ids), 3.0), else_=0.0)
    else:
        topic_score = literal_column('0.0')
    if brand_entity_ids:
        brand_score = case((ContentEntity.entity_id.in_(brand_entity_ids), 2.0), else_=0.0)
    else:
        brand_score = literal_column('0.0')
    category_score = case((Content.category_id == category_id, 1.5), else_=0.0)
    if event_id:
        event_score = case((Content.id.in_(select(Content.id).join(Article, Content.object_id == Article.id).where(Content.object_type == 'article', Article.event_id == event_id)), 1.7), else_=0.0)
    else:
        event_score = literal_column('0.0')
    section_score = case((Content.section_id == section_id, 0.5), else_=0.0)
    epoch_diff = func.extract('epoch', func.now() - Content.published_at)
    age_days = epoch_diff / 86400.0
    recency_score = cast(0.8 / (1.0 + age_days / 30.0), Float)
    popularity_score = cast(func.log(1 + Content.view_count) * 0.4, Float)
    relevance_expr = func.sum(topic_score) + func.max(brand_score) + func.max(category_score) + func.max(event_score) + func.max(section_score) + func.max(recency_score) + func.max(popularity_score)
    stmt = build_content_stmt(active_only=True, published_only=True, eager_load='default')
    stmt = stmt.outerjoin(Content.content_entities).where(Content.id != content_id)
    stmt = build_ranked_content_stmt(stmt, relevance_expr, 'relevance_score')
    stmt = stmt.having(relevance_expr > 0)
    if limit:
        stmt = stmt.limit(limit)
    return fetch_serialized_contents(stmt, session)