from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse
from sqlalchemy import func, select
from app.core.extensions import db
from app.shared.utils.slug import generate_slug
from app.shared.constants.taxonomy import TRUSTED_SOURCES
from ..models import Article, Content, Event
from ...taxonomy.models import AttributeFacet, GenderFacet, IntentFacet, PriceTierFacet, Source, Category, Entity, Location
from app.domains.relationships import ContentEntity, ArticleSource, ArticleCategory
from app.domains.interaction.models import Comment, Reaction, View
from app.domains.serialization_utils import safe_attr
from app.shared.utils.orm_helpers import get_model_registry
from .content_access import resolve

def create_content(obj, object_type, published_at, session=None, **kwargs):
    session = session or db.session
    stmt = select(Content).where(Content.object_type == object_type, Content.object_id == obj.id)
    existing = session.execute(stmt).scalars().first()
    if existing:
        changed = False
        if existing.published_at != published_at:
            existing.published_at = published_at
            changed = True
        for k, v in kwargs.items():
            if getattr(existing, k) != v:
                setattr(existing, k, v)
                changed = True
        return (existing, changed)
    content = Content(object_type=object_type, object_id=obj.id, published_at=published_at, title=safe_attr(obj, 'title', ''), preview_text=safe_attr(obj, 'preview_text', ''), **kwargs)
    session.add(content)
    session.flush()
    return (content, False)

def get_or_create_content(object_type, external_id, obj_factory, title_fallback=None, url_fallback=None, session=None, **kwargs):
    model = get_model_registry().get(object_type)
    if not model:
        return (None, False)
    session = session or db.session
    obj = None
    is_new = False
    if external_id and hasattr(model, 'external_id'):
        stmt = select(model).where(model.external_id == external_id)
        obj = session.execute(stmt).scalars().first()
    if not obj and url_fallback:
        canonical_url = kwargs.get('canonical_url')
        if object_type == 'article':
            urls_to_check = [u for u in (url_fallback, canonical_url) if u]
            if urls_to_check:
                stmt_url = select(ArticleSource).where(ArticleSource.url.in_(urls_to_check))
                res = session.execute(stmt_url).scalars().first()
                if res:
                    obj = session.get(model, res.article_id)
                elif canonical_url:
                    stmt_art = select(model).where(model.canonical_url == canonical_url)
                    obj = session.execute(stmt_art).scalars().first()
        elif hasattr(model, 'url'):
            stmt_url = select(model).where(model.url == url_fallback)
            obj = session.execute(stmt_url).scalars().first()
    if not obj and title_fallback and hasattr(model, 'title'):
        normalized_title = title_fallback.lower().strip()
        stmt_title = select(model).where(func.lower(model.title) == normalized_title)
        obj = session.execute(stmt_title).scalars().first()
    if not obj:
        obj = obj_factory()
        session.add(obj)
        session.flush()
        is_new = True
    return (obj, is_new)

def sync_content_fields(content, obj, object_type: str) -> None:
    content.title = safe_attr(obj, 'title', '')
    content.preview_text = safe_attr(obj, 'preview_text', None)
    content.score = safe_attr(obj, 'quality_score', 0.0)
    match object_type:
        case 'article':
            content.is_published = safe_attr(obj, 'status') == 'published'


def link_article_sources(article, data, session=None) -> bool:
    session = session or db.session
    source_name = data.get('source_name')
    url = data.get('url')
    published_at = data.get('published_at')
    if not source_name or not url:
        return False
    slug = generate_slug(source_name)
    source = Source.get_by_slug(slug, session)
    if not source:
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        source = session.query(Source).filter_by(domain=domain).first()
        if not source:
            authority_score = 50
            for s_trusted in TRUSTED_SOURCES:
                t_domain = s_trusted['domain'].lower()
                if domain == t_domain or domain.endswith('.' + t_domain):
                    authority_score = s_trusted.get('score', 70)
                    break
            er_source = data.get('er_source') or {}
            ranking_data = er_source.get('ranking') or {}
            importance_rank = ranking_data.get('importanceRank')
            if importance_rank:
                if importance_rank <= 1000:
                    authority_score = max(authority_score, 90)
                elif importance_rank <= 10000:
                    authority_score = max(authority_score, 75)
                elif importance_rank <= 50000:
                    authority_score = max(authority_score, 60)
            source = Source(name=source_name, slug=slug, domain=domain, authority_score=authority_score, is_active=True)
            session.add(source)
            session.flush()
    stmt_url = select(ArticleSource).where(ArticleSource.url == url)
    existing = session.execute(stmt_url).scalars().first()
    if existing:
        return False
    stmt_relation = select(ArticleSource).where(ArticleSource.article_id == article.id, ArticleSource.source_id == source.id)
    existing_relation = session.execute(stmt_relation).scalars().first()
    if existing_relation:
        return False
    relation = ArticleSource(article_id=article.id, source_id=source.id, url=url, published_at=published_at)
    session.add(relation)
    session.flush()
    article.update_primary_source()
    return True

def _apply_facets_and_attributes(content, data, updated_relationships, session):
    facets_data = data.get('facets', {})
    if facets_data.get('attributes'):
        updated_relationships.setdefault('facets', {})
        updated_relationships['facets'].setdefault('attributes', [])
        for slug in facets_data['attributes']:
            attr = AttributeFacet.get_or_create(slug, session)
            if attr:
                if content.add_attribute(attr):
                    updated_relationships['facets']['attributes'].append(attr.slug)
    if facets_data.get('gender') or facets_data.get('intent') or facets_data.get('price_tier'):
        updated_relationships.setdefault('facets', {})
    if facets_data.get('gender'):
        g = GenderFacet.get_by_slug(facets_data['gender'], session)
        if g and content.gender_id != g.id:
            content.gender_id = g.id
            updated_relationships['facets']['gender'] = g.slug
    if facets_data.get('intent'):
        i = IntentFacet.get_or_create(facets_data['intent'], session)
        if i and content.intent_id != i.id:
            content.intent_id = i.id
            updated_relationships['facets']['intent'] = i.slug
    if facets_data.get('price_tier'):
        p = PriceTierFacet.get_or_create(facets_data['price_tier'], session)
        if p and content.price_tier_id != p.id:
            content.price_tier_id = p.id
            updated_relationships['facets']['price_tier'] = p.slug

def _apply_events_and_categories(content, data, obj, updated_relationships, session):
    if content.object_type != 'article':
        return
    if data.get('er_event_data') or data.get('er_event_uri'):
        event_data = data.get('er_event_data') or {}
        event_uri = event_data.get('uri') or data.get('er_event_uri')
        if event_uri:
            title_raw = event_data.get('title')
            title_str = title_raw.get('eng', str(title_raw)) if isinstance(title_raw, dict) else title_raw or data.get('title')
            sum_raw = event_data.get('summary')
            summary_str = sum_raw.get('eng', str(sum_raw)) if isinstance(sum_raw, dict) else sum_raw
            event_date_str = event_data.get('eventDate')
            event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00')) if event_date_str else None
            event = Event.get_or_create(external_uri=event_uri, session=session, title=title_str, summary=summary_str, event_date=event_date, article_count=event_data.get('articleCount', 0), importance=event_data.get('importance'), image_url=event_data.get('image'), event_type=event_data.get('type'))
            if event and (obj.event_id is None or obj.event_id != event.id):
                obj.event_id = event.id
                updated_relationships['event'] = event.external_uri
    if data.get('er_categories'):
        for cat_data in data['er_categories']:
            cat_label = cat_data if isinstance(cat_data, str) else cat_data.get('name', cat_data.get('label', ''))
            wgt = 0.0
            if isinstance(cat_data, dict):
                wgt = float(cat_data.get('wgt', 0.0))
            if not cat_label:
                continue
            cat = Category.get_or_create_from_path(cat_label, session=session)
            if cat:
                existing_link = session.query(ArticleCategory).filter_by(article_id=obj.id, category_id=cat.id).first()
                if existing_link:
                    if existing_link.weight != wgt:
                        existing_link.weight = wgt
                else:
                    new_link = ArticleCategory(article=obj, category=cat, weight=wgt)
                    session.add(new_link)
                    updated_relationships.setdefault('categories', []).append(cat.slug)

def _apply_entities_and_locations(content, data, updated_relationships, session):
    if content.object_type == 'article' and data.get('er_location'):
        loc_data = data['er_location']
        if isinstance(loc_data, dict):
            loc_label = (loc_data.get('label') or {}).get('eng')
            country_data = loc_data.get('country') or {}
            country_label = (country_data.get('label') or {}).get('eng')
            if loc_label:
                loc = Location.get_or_create(loc_label, session=session, country_name=country_label)
                if loc and loc not in content.locations:
                    content.locations.append(loc)
                    updated_relationships.setdefault('locations', []).append(loc.slug)
    if data.get('er_concepts'):
        for concept in data['er_concepts']:
            if isinstance(concept, str):
                concept_uri = None
                concept_label = concept
                entity_type = 'tag'
                score = 0
            else:
                concept_uri = concept.get('uri')
                concept_label = concept.get('label', {}).get('eng', concept.get('label', '')) if isinstance(concept.get('label'), dict) else concept.get('label', '')
                entity_type = concept.get('type', 'tag')
                score = concept.get('score', 0)
            if not concept_label:
                continue
            entity = Entity.get_or_create(name=concept_label, session=session, external_uri=concept_uri, entity_type=entity_type, provider='event_registry', image_url=concept.get('image'))
            if entity:
                origin = 'diffbot' if data.get('ingestion_method') == 'diffbot' else 'event_registry'
                ce = ContentEntity.get_or_create(content_id=content.id, entity_id=entity.id, session=session, origin=origin, relevance_score=score, confidence=score / 100.0 if score > 1 else score)
                updated_relationships.setdefault('entities', []).append(entity.slug)
            if entity_type in ('location', 'place', 'loc'):
                location_data = concept.get('location') or {}
                country_data = location_data.get('country') or {}
                label_data = country_data.get('label') or {}
                country_label = label_data.get('eng')
                loc = Location.get_or_create(concept_label, session=session, country_name=country_label)
                if loc and loc not in content.locations:
                    content.locations.append(loc)
                    updated_relationships.setdefault('locations', []).append(loc.slug)

def _apply_sources(content, data, obj, updated_relationships, session):
    if content.object_type == 'article':
        if obj:
            extended_metadata = data.get('extended_metadata', {})
            if not data.get('source_name') and 'siteName' in extended_metadata:
                data['source_name'] = extended_metadata['siteName']
            if not data.get('url'):
                data['url'] = obj.url
            link_article_sources(obj, data, session=session)
            if obj.preferred_source_relation and obj.preferred_source_relation.source:
                content.source_id = obj.preferred_source_relation.source.id
                updated_relationships['sources'] = [s.source.slug for s in obj.article_sources]
                if data.get('source_name'):
                    updated_relationships['sources'].append(data.get('source_name').lower())
    elif content.object_type in ('video', 'post'):
        platform_name = data.get('platform') or content.object_type
        slug = generate_slug(platform_name)
        source = Source.get_by_slug(slug, session)
        if not source:
            domain = f'{slug}.com'
            source = Source(name=platform_name.capitalize(), slug=slug, domain=domain, authority_score=100, is_active=True)
            session.add(source)
            session.flush()
        content.source_id = source.id
        updated_relationships['sources'] = [slug]

def apply_relationships(content, data, session=None) -> dict:
    session = session or db.session
    updated_relationships = defaultdict(list)
    obj = resolve(content, session=session)
    _apply_facets_and_attributes(content, data, updated_relationships, session)
    if obj:
        _apply_events_and_categories(content, data, obj, updated_relationships, session)
    _apply_entities_and_locations(content, data, updated_relationships, session)
    _apply_sources(content, data, obj, updated_relationships, session)
    return updated_relationships

def delete_content_and_relations(content: Content, session=None) -> None:
    session = session or db.session
    cid = content.id
    for model in (Comment, Reaction, View):
        session.execute(model.__table__.delete().where((model.target_type == 'content') & (model.target_id == cid)))
    match content.object_type:
        case 'article':
            session.execute(Article.__table__.delete().where(Article.id == content.object_id))
    session.delete(content)

def execute_bulk_content_actions(action, contents, category_id=None, session=None):
    session = session or db.session
    match action:
        case 'activate':
            for c in contents:
                c.is_active = True
        case 'deactivate':
            for c in contents:
                c.is_active = False
        case 'publish':
            for c in contents:
                c.is_published = True
        case 'unpublish' | 'review':
            for c in contents:
                c.is_published = False
        case 'recategorize':
            if category_id is None:
                raise ValueError('Category ID is required for recategorize action')
            category = session.get(Category, int(category_id))
            if not category:
                raise ValueError('Target category not found')
            for c in contents:
                c.category_id = category.id
        case 'delete':
            for c in contents:
                delete_content_and_relations(c, session)
        case _:
            raise ValueError('Unsupported bulk action')

def recalculate_content_score(content, target_obj, session=None):
    session = session or db.session
    quality_score = safe_attr(target_obj, 'quality_score', 0.0)
    authority_score = safe_attr(content.source, 'authority_score', 0.0)
    authority_score_normalized = authority_score / 100.0
    sentiment = safe_attr(target_obj, 'sentiment_score', 0.0)
    sentiment_boost = 0.1 if sentiment > 0.2 else -0.05 if sentiment < -0.2 else 0.0
    entities_count = len(content.content_entities)
    entity_richness = min(entities_count, 10) / 10.0
    category_weight_max = 0.0
    if content.object_type == 'article':
        cat_weight = session.query(func.max(ArticleCategory.weight)).filter_by(article_id=content.object_id).scalar()
        category_weight_max = (cat_weight or 0.0) / 100.0
    content_html = bool(safe_attr(target_obj, 'content_html', None))
    summary = bool(safe_attr(target_obj, 'summary', None))
    image_url = bool(safe_attr(target_obj, 'image_url', None) or safe_attr(target_obj, 'thumbnail_url', None))
    completeness = (0.5 if content_html else 0.0) + (0.3 if summary else 0.0) + (0.2 if image_url else 0.0)
    content.score = quality_score * 0.3 + authority_score_normalized * 0.25 + sentiment_boost * 0.1 + entity_richness * 0.15 + category_weight_max * 0.1 + completeness * 0.1
    return content.score