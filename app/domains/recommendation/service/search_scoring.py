import math
from datetime import datetime, timezone
from app.domains.recommendation.service.query_preprocessor import (
    _normalize as normalize_search_query,
    _tokenize as tokenize_query,
    _detect_intent,
)

TEXT_WEIGHT = 4.0
POPULARITY_WEIGHT = 0.8
FRESHNESS_WEIGHT = 0.6
INTENT_WEIGHT = 1.2


def detect_search_intent(query: str) -> dict:
    normalized = normalize_search_query(query)
    tokens = tokenize_query(normalized)
    return _detect_intent(normalized, tokens)


def _value(obj, key, default=''):
    if not obj:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _joined_names(values):
    return ' '.join((str(_value(value, 'name', '')) for value in values or []))


def _text_relevance(query, result):
    terms = tokenize_query(query)
    if not terms:
        return 0.0
    target = result.get('target') or {}
    category = result.get('category') or {}
    brand = result.get('brand') or {}
    title = result.get('name') or _value(target, 'title', '')
    slug = result.get('slug') or _value(category, 'slug', '')
    primary = ' '.join([str(title or ''), str(slug or '')]).lower()
    secondary = ' '.join([
        str(result.get('description') or ''),
        str(_value(target, 'preview_text', '')),
        str(_value(target, 'description', '')),
        str(_value(category, 'name', '')),
        str(_value(brand, 'name', '')),
        _joined_names(result.get('topics')),
        _joined_names(result.get('brands')),
    ]).lower()
    score = 0.0
    phrase = normalize_search_query(query)
    if phrase and phrase in primary:
        score += 3.0
    if phrase and phrase in secondary:
        score += 1.5
    for term in terms:
        if term in primary:
            score += 1.2
        elif term in secondary:
            score += 0.6
    return score * TEXT_WEIGHT


def _freshness_score(result):
    raw_date = result.get('published_at') or result.get('created_at')
    if not raw_date:
        return 0.0
    if isinstance(raw_date, str):
        try:
            raw_date = datetime.fromisoformat(raw_date)
        except ValueError:
            return 0.0
    if raw_date.tzinfo is None:
        raw_date = raw_date.replace(tzinfo=timezone.utc)
    age_days = max((datetime.now(timezone.utc) - raw_date).days, 0)
    return FRESHNESS_WEIGHT / (1 + age_days / 30)


def _popularity_score(result):
    signals = [
        result.get('view_count') or 0,
        result.get('comment_count') or 0,
        result.get('review_count') or 0,
        result.get('click_count') or 0,
    ]
    target = result.get('target') or {}
    signals.append(_value(target, 'upvotes', 0) or 0)
    return math.log1p(sum(signals)) * POPULARITY_WEIGHT


def _intent_score(result, intent):
    result_type = result.get('search_type')
    if result_type == 'product':
        return intent['shopping_score'] * INTENT_WEIGHT
    return intent['content_score'] * INTENT_WEIGHT


def attach_score(result, query, intent):
    scored = dict(result)
    scored['_search'] = {
        'score': (
            _text_relevance(query, scored)
            + _popularity_score(scored)
            + _freshness_score(scored)
            + _intent_score(scored, intent)
        ),
        'type': scored.get('search_type'),
    }
    return scored