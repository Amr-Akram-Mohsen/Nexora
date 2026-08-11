from __future__ import annotations
import re
from dataclasses import dataclass, field
_CONTENT_INTENT_TERMS: frozenset[str] = frozenset({'how', 'guide', 'tutorial', 'review', 'tips', 'tricks', 'what', 'why', 'explained', 'news', 'update', 'analysis'})
_SHOPPING_INTENT_TERMS: frozenset[str] = frozenset({'buy', 'best', 'price', 'compare', 'top', 'vs', 'deal', 'deals', 'product', 'products', 'cheap', 'cheap', 'affordable', 'discount', 'offer', 'shop'})
_PRODUCT_HINT_TERMS: frozenset[str] = frozenset({'phone', 'laptop', 'camera', 'headphones', 'watch', 'perfume', 'tablet', 'earbuds', 'speaker', 'monitor', 'keyboard', 'mouse', 'console', 'router', 'charger', 'cable'})
@dataclass
class ParsedQuery:
    raw: str = ''
    normalized: str = ''
    tokens: list[str] = field(default_factory=list)
    tsquery_safe: str = ''
    intent: dict = field(default_factory=lambda: {'content_score': 0, 'shopping_score': 0})
def _normalize(query: str) -> str:
    return ' '.join((query or '').strip().lower().split())
def _tokenize(normalized: str) -> list[str]:
    return re.findall('[a-z0-9]{2,}', normalized)
def _make_tsquery_safe(query: str) -> str:
    cleaned = re.sub('[&|!:<>()@]', ' ', query)
    return ' '.join(cleaned.split())
def _detect_intent(normalized: str, tokens: list[str]) -> dict:
    token_set = set(tokens)
    content_score = sum((1 for t in _CONTENT_INTENT_TERMS if t in token_set))
    shopping_score = sum((1 for t in _SHOPPING_INTENT_TERMS if t in token_set))
    shopping_score += sum((1 for t in _PRODUCT_HINT_TERMS if t in token_set))
    if 'what is' in normalized or 'how to' in normalized:
        content_score += 2
    if f' vs ' in f' {normalized} ':
        shopping_score += 2
        content_score += 1
    return {'content_score': content_score, 'shopping_score': shopping_score}
def preprocess_query(raw_query: str) -> ParsedQuery:
    raw = (raw_query or '').strip()
    normalized = _normalize(raw)
    tokens = _tokenize(normalized)
    tsquery_safe = _make_tsquery_safe(normalized)
    intent = _detect_intent(normalized, tokens)
    return ParsedQuery(raw=raw, normalized=normalized, tokens=tokens, tsquery_safe=tsquery_safe, intent=intent)