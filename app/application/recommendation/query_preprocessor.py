"""
Query Preprocessor — Shared Search Utility
==========================================
Normalizes, tokenizes, and classifies raw user search queries.

Used by:
  - search_workflow  (unified search)
  - suggestions endpoint  (live autocomplete)
  - future recommendation triggers

All logic is pure Python — no DB calls, no I/O.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Intent signal term sets
# ---------------------------------------------------------------------------

_CONTENT_INTENT_TERMS: frozenset[str] = frozenset({
    "how", "guide", "tutorial", "review", "tips", "tricks",
    "what", "why", "explained", "news", "update", "analysis",
})

_SHOPPING_INTENT_TERMS: frozenset[str] = frozenset({
    "buy", "best", "price", "compare", "top", "vs",
    "deal", "deals", "product", "products", "cheap", "cheap",
    "affordable", "discount", "offer", "shop",
})

_PRODUCT_HINT_TERMS: frozenset[str] = frozenset({
    "phone", "laptop", "camera", "headphones", "watch", "perfume",
    "tablet", "earbuds", "speaker", "monitor", "keyboard", "mouse",
    "console", "router", "charger", "cable",
})


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class ParsedQuery:
    """
    Normalized, classified query ready for use in search or recommendation.

    Attributes:
        raw:            The original user-supplied string (stripped).
        normalized:     Lowercased, collapsed-whitespace version.
        tokens:         Individual word tokens (len >= 2).
        tsquery_safe:   A safe string for passing to PostgreSQL ts_query functions.
                        Special chars that break tsquery are removed.
        intent:         Dict with ``content_score`` and ``shopping_score`` signals.
    """
    raw: str = ""
    normalized: str = ""
    tokens: list[str] = field(default_factory=list)
    tsquery_safe: str = ""
    intent: dict = field(default_factory=lambda: {"content_score": 0, "shopping_score": 0})


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def _normalize(query: str) -> str:
    """Lowercase, collapse whitespace."""
    return " ".join((query or "").strip().lower().split())


def _tokenize(normalized: str) -> list[str]:
    """Split into alphanumeric tokens of length >= 2."""
    return re.findall(r"[a-z0-9]{2,}", normalized)


def _make_tsquery_safe(query: str) -> str:
    """
    Strip characters that PostgreSQL tsquery operators would misinterpret
    when passed to ``websearch_to_tsquery`` or ``plainto_tsquery``.

    Keeps: letters, digits, spaces, hyphens, apostrophes.
    Strips: ``& | ! : ( ) < >`` and other shell-like punctuation.
    """
    cleaned = re.sub(r"[&|!:<>()@]", " ", query)
    return " ".join(cleaned.split())  # collapse extra whitespace


def _detect_intent(normalized: str, tokens: list[str]) -> dict:
    """Classify the query as content-seeking vs shopping-seeking."""
    token_set = set(tokens)

    content_score = sum(1 for t in _CONTENT_INTENT_TERMS if t in token_set)
    shopping_score = sum(1 for t in _SHOPPING_INTENT_TERMS if t in token_set)
    shopping_score += sum(1 for t in _PRODUCT_HINT_TERMS if t in token_set)

    # Phrase-level boosts
    if "what is" in normalized or "how to" in normalized:
        content_score += 2
    if f" vs " in f" {normalized} ":
        shopping_score += 2
        content_score += 1  # "X vs Y" also surfaces comparison articles

    return {"content_score": content_score, "shopping_score": shopping_score}


def preprocess_query(raw_query: str) -> ParsedQuery:
    """
    Full query preprocessing pipeline.

    Args:
        raw_query:  User-supplied search string (any encoding, any case).

    Returns:
        A :class:`ParsedQuery` dataclass with all derived fields populated.

    Example::

        pq = preprocess_query("Best AirPods 2025")
        # pq.normalized  → "best airpods 2025"
        # pq.tokens      → ["best", "airpods", "2025"]
        # pq.tsquery_safe → "best airpods 2025"
        # pq.intent      → {"content_score": 0, "shopping_score": 2}
    """
    raw = (raw_query or "").strip()
    normalized = _normalize(raw)
    tokens = _tokenize(normalized)
    tsquery_safe = _make_tsquery_safe(normalized)
    intent = _detect_intent(normalized, tokens)

    return ParsedQuery(
        raw=raw,
        normalized=normalized,
        tokens=tokens,
        tsquery_safe=tsquery_safe,
        intent=intent,
    )
