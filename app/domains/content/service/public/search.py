from sqlalchemy import func, select, case as sa_case
from app.domains.content.models import Content
from app.domains.content.service.content_access import assign_target_to_contents
from app.domains.content.service.query.utils import CONTENT_LIST_EAGER_LOADS
from app.core.extensions import db

def build_content_search_vector(content, body_text=''):
    return func.setweight(func.to_tsvector('english', func.coalesce(content.title, '')), 'A').op('||')(func.setweight(func.to_tsvector('english', func.coalesce(content.preview_text, '')), 'B')).op('||')(func.setweight(func.to_tsvector('english', func.coalesce(content.search_text, '')), 'C')).op('||')(func.setweight(func.to_tsvector('english', func.coalesce(body_text, '')), 'D'))

def populate_content_search_fields(content, obj, object_type):
    target_fields_map = {'video': ['channel_name'], 'post': ['author', 'subreddit'], 'article': ['author', 'source_name']}
    source = ' '.join(filter(None, [getattr(obj, field, '') for field in target_fields_map.get(object_type, [])]))
    canonical = getattr(obj, 'canonical_url', '')
    attribute_names = ' '.join((attr.name for attr in content.attributes))
    category_name = content.category.name if content.category else ''
    gender_name = content.gender.name if content.gender else ''
    intent_name = content.intent.name if content.intent else ''
    price_tier_name = content.price_tier.name if content.price_tier else ''
    entity_names = ' '.join((ce.entity.name for ce in content.content_entities if ce.entity))
    event_title = ''
    if hasattr(obj, 'event') and obj.event:
        event_title = obj.event.title or ''
    body_text = ''
    if object_type in ('article', 'post'):
        body_text = getattr(obj, 'content_text', '') or ''
    elif object_type == 'video':
        body_text = getattr(obj, 'description', '') or ''
    search_str = ' '.join(filter(None, [content.title, content.preview_text, canonical, source, attribute_names, category_name, gender_name, intent_name, price_tier_name, entity_names, event_title]))
    compounds_map = {'smartwatches': 'smart watches smartwatch', 'smartwatch': 'smart watches smartwatch', 'earbuds': 'ear buds earbud', 'earbud': 'ear buds earbud', 'airpods': 'air pods airpod earbuds wireless earphones', 'airpod': 'air pods airpod earbuds wireless earphones', 'noisecancelling': 'noise cancelling noise-cancelling anc', 'noisecanceling': 'noise cancelling noise-canceling anc', 'smartphone': 'smart phone mobile phone handset', 'smartphones': 'smart phones mobile phones handsets', 'iphone': 'i phone apple iphone ios mobile', 'android': 'android google mobile smartphone', 'macbook': 'mac book apple laptop macbook', 'ipad': 'i pad apple tablet ipad', 'laptop': 'laptop notebook computer portable', 'playstation': 'play station sony ps5 ps4 gaming console', 'xbox': 'xbox microsoft gaming console', 'nintendo': 'nintendo switch gaming portable', 'bluetooth': 'bluetooth wireless bt', 'wifi': 'wi-fi wifi wireless network', '5g': '5g fifth generation mobile network'}
    extra_terms = []
    search_str_lower = search_str.lower()
    for compound, expansion in compounds_map.items():
        if compound in search_str_lower:
            extra_terms.append(expansion)
    if extra_terms:
        search_str += ' ' + ' '.join(extra_terms)
    content.search_text = search_str
    content.search_vector = build_content_search_vector(content, body_text=body_text)

def get_search_contents(query, limit=80, session=None):
    session = session or db.session
    query = (query or '').strip()
    if not query:
        return []
    web_q = func.websearch_to_tsquery('english', query)
    plain_q = func.plainto_tsquery('english', query)
    empty_q = func.to_tsquery('')
    search_query = func.coalesce(func.nullif(web_q, empty_q), plain_q)
    rank = func.ts_rank_cd(Content.search_vector, search_query)
    title_boost = sa_case((func.lower(Content.title).startswith(query.lower()), 0), else_=1)
    stmt = select(Content).options(*CONTENT_LIST_EAGER_LOADS).where(Content.is_active, Content.is_published, Content.search_vector.op('@@')(search_query)).order_by(title_boost, rank.desc(), Content.view_count.desc(), Content.score.desc(), Content.published_at.desc()).limit(limit)
    contents = session.execute(stmt).scalars().all()
    return assign_target_to_contents(contents, session=session)