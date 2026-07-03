"""
Stage 5: Block List Validation & Cleanup
-----------------------------------------
Quality gate applied to the list of content blocks produced by stage 4.

Sub-passes (in order):
  A. Navigation block filter — drop blocks that are purely site links.
  B. Garbage block removal   — drop junk phrases, emoji-only, single-punctuation.
  C. Deduplication           — drop exact + near-duplicate paragraphs/images/headings.
  D. Paragraph merging       — merge adjacent fragments only when safe.
  E. Quality gate            — drop whole result if too sparse.

Returns:
    List[dict] on success, or None if the quality gate fails.
"""
import re
import difflib
from typing import Optional

# ── Type groups ──────────────────────────────────────────────────────────────────────
_TEXT_BLOCK_TYPES  = {"paragraph", "heading", "quote", "list", "price", "date"}
_WORD_COUNT_TYPES  = {"paragraph", "heading"}  # price/date excluded from word-count quality gate
_PASS_THROUGH_TYPES = {"image", "code", "table", "embed", "divider", "price", "date"}

# ── Regex constants ───────────────────────────────────────────────────────────
_BARE_LINK_RE   = re.compile(r'^\[.+?\]\(https?://[^\)]+\)$')
_RAW_URL_RE     = re.compile(r'^https?://\S+$')
_ALL_LINKS_RE   = re.compile(r'\[(?:[^\]]*)\]\((https?://[^\)]+)\)')
_EMOJI_ONLY_RE  = re.compile(
    r'^[\s\U0001F600-\U0001F64F\U0001F300-\U0001F5FF'
    r'\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\u2600-\u26FF\u2700-\u27BF]+$'
)
_PUNCT_ONLY_RE  = re.compile(r'^[\s\W_]+$')  # only whitespace and non-word chars

# Known garbage phrases (matched case-insensitively after stripping HTML tags)
_GARBAGE_PHRASES = frozenset({
    # Advertising
    "advertisement", "sponsored", "promoted", "partner content", "paid content",
    # UI states
    "loading", "loading...", "please wait", "read more", "continue reading",
    # Share / social
    "share", "share this", "share this article", "tweet", "tweet this",
    "pin it", "save", "print", "email this", "send",
    "copy link", "copy url", "copy to clipboard",
    "follow", "follow us", "follow us on", "follow author", "follow the author",
    "like", "bookmark", "save this article", "save this",
    # Subscribe
    "subscribe", "subscribe now", "sign up", "sign up now",
    "newsletter", "get the newsletter", "join the newsletter",
    "email alerts", "get alerts",
    # Privacy / cookies
    "cookie policy", "privacy policy", "terms of service",
    "accept", "decline", "accept cookies", "manage cookies",
    "privacy settings", "cookie settings",
    # Navigation
    "back to top", "scroll to top", "top", "menu",
    "next", "previous", "newer", "older",
    # Comments
    "comments", "leave a comment", "add a comment", "no comments yet",
    "be the first to comment",
    # Article structure UI
    "table of contents", "in this article",
    # Tags / classification
    "tags:", "filed under:", "topics:", "labels:", "keywords:",
    # Actions
    "more", "see more", "view more", "load more", "see all", "view all", "show all",
    "click here", "learn more", "find out more",
    # Video
    "watch", "watch now", "watch video", "play",
    # Commerce
    "buy now", "shop now", "get it here", "order now",
    "free trial", "start free trial",
    # Copyright
    "copyright", "all rights reserved",
    # Temporal metadata (publisher article dates — already in Article model)
    "published", "updated", "first published", "last updated", "last modified",
    # Publisher-specific section headings
    "featured articles", "featured stories", "featured content",
    "industry announcements", "newsletters", "around the web",
    # Author bio
    "about the author", "written by", "more from the author",
    "print article", "print this article",
    # Print/email buttons
    "email article", "email this article",
    # Related content labels
    "related stories", "related articles", "related posts",
    "recommended", "recommended for you",
    # Engagement
    "popular this week", "most read", "most read this week",
    # Misc UI
    "continue reading below", "article continues below",
})


# ── Source domain helpers ─────────────────────────────────────────────────────

def _url_is_source_domain(url: str, source_domain: str) -> bool:
    if not source_domain:
        return False
    try:
        host = url.split('/')[2].lower()
        if host.startswith('www.'):
            host = host[4:]
        return host == source_domain or host.endswith('.' + source_domain)
    except Exception:
        return False


# ── A. Navigation block filter ────────────────────────────────────────────────

def _is_navigation_block(block: dict, source_domain: str = "") -> bool:
    """
    Returns True if this block is purely a navigation link collection:
      A) All items/text are bare hyperlinks (classic link-only menu).
      B) All hyperlinks in the block target the source domain.
    Price and date blocks are never navigation blocks.
    """
    btype = block.get("type")

    # Price and date blocks pass through
    if btype in ("price", "date"):
        return False

    if btype == "list":
        items = block.get("items", [])
        if not items:
            return False
        # Strip HTML tags for analysis
        clean_items = [re.sub(r'<[^>]+>', '', it) for it in items]
        bare_count  = sum(
            1 for it in items
            if _BARE_LINK_RE.match(it.strip()) or _RAW_URL_RE.match(it.strip())
        )
        if bare_count / len(items) >= 0.8:
            return True
        if source_domain:
            all_urls = [url for it in items for url in _ALL_LINKS_RE.findall(it)]
            if all_urls and all(_url_is_source_domain(u, source_domain) for u in all_urls):
                return True
        return False

    if btype == "paragraph":
        text = re.sub(r'<[^>]+>', '', block.get("text", "")).strip()
        if _BARE_LINK_RE.match(text) or _RAW_URL_RE.match(text):
            return True
        if source_domain:
            all_urls = _ALL_LINKS_RE.findall(block.get("text", ""))
            if all_urls and all(_url_is_source_domain(u, source_domain) for u in all_urls):
                return True
        return False

    return False


# ── B. Garbage block removal ──────────────────────────────────────────────────

def _strip_html_tags(text: str) -> str:
    """Quick strip of HTML tags for analysis purposes."""
    return re.sub(r'<[^>]+>', '', text)


def _is_garbage_block(block: dict) -> bool:
    """
    Returns True if this block carries no real article content:
      - Pure whitespace, punctuation, or emoji
      - Text matches a known garbage phrase exactly
      - Very short repeated decorative text
    Price and date blocks are never classified as garbage.
    """
    btype = block.get("type")

    # Price and date blocks always pass through
    if btype in ("price", "date"):
        return False

    if btype in ("paragraph", "heading", "quote"):
        raw  = block.get("text", "")
        text = _strip_html_tags(raw).strip()

        if not text:
            return True
        # Pure punctuation / symbols / emoji
        if _PUNCT_ONLY_RE.match(text):
            return True
        if _EMOJI_ONLY_RE.match(text):
            return True
        # Known garbage phrase
        if text.lower() in _GARBAGE_PHRASES:
            return True
        # Very short (≤ 3 words) and all-caps — likely a label/button
        words = text.split()
        if len(words) <= 3 and text == text.upper() and len(text) <= 30:
            return True

        return False

    if btype == "list":
        items = block.get("items", [])
        if not items:
            return True
        # All items are garbage
        return all(_is_garbage_block({"type": "paragraph", "text": it}) for it in items)

    return False


# ── C. Deduplication ──────────────────────────────────────────────────────────

def _text_key(text: str) -> str:
    """Normalize text for deduplication comparison."""
    return re.sub(r'\s+', ' ', _strip_html_tags(text).lower().strip())


def _deduplicate(blocks: list[dict]) -> tuple[list[dict], int]:
    """
    Remove exact and near-duplicate blocks.
    Returns (deduped_blocks, removed_count).
    """
    seen_paragraph_keys: list[str] = []
    seen_heading_keys:   set[str]  = set()
    seen_image_urls:     set[str]  = set()
    result   = []
    removed  = 0

    for block in blocks:
        btype = block.get("type")

        if btype == "image":
            url = block.get("url", "")
            if url in seen_image_urls:
                removed += 1
                continue
            seen_image_urls.add(url)
            result.append(block)
            continue

        if btype == "heading":
            key = _text_key(block.get("text", ""))
            if key in seen_heading_keys:
                removed += 1
                continue
            seen_heading_keys.add(key)
            result.append(block)
            continue

        if btype == "paragraph":
            key = _text_key(block.get("text", ""))
            if not key:
                removed += 1
                continue
            # Exact duplicate
            if key in seen_paragraph_keys:
                removed += 1
                continue
            # Near-duplicate: compare against last N seen paragraphs
            # Only check within a sliding window to stay O(n) efficient
            is_near_dup = False
            for seen_key in seen_paragraph_keys[-20:]:
                if len(key) < 40 or len(seen_key) < 40:
                    continue  # short fragments are too ambiguous to near-dedup
                ratio = difflib.SequenceMatcher(None, key[:300], seen_key[:300]).ratio()
                if ratio >= 0.92:
                    is_near_dup = True
                    break
            if is_near_dup:
                removed += 1
                continue
            seen_paragraph_keys.append(key)
            result.append(block)
            continue

        # Other block types pass through unchanged
        result.append(block)

    return result, removed


# ── D. Paragraph merging ──────────────────────────────────────────────────────

# Sentence-ending punctuation that signals a complete thought.
# We NEVER merge a paragraph that ends with one of these into the next.
_SENTENCE_ENDERS = frozenset({'.', '?', '!', '"', '\u201d', '\u2019'})

# Explicit continuation markers — if a paragraph ends with these, it is
# almost certainly a fragment split by the extractor.
_CONTINUATION_ENDERS = frozenset({',', '—', '–', '-', ':'})


def _can_merge(first: dict, second: dict) -> bool:
    """
    Returns True ONLY when it is safe to merge two adjacent paragraph blocks.

    Conservative rules (all must be true):
      1. Both blocks are `paragraph` type.
      2. The first paragraph ends with an explicit continuation marker
         (comma, em-dash, en-dash, colon) — which unambiguously signals
         it was split mid-thought.
         OR both paragraphs are very short (≤ 60 chars) and the first
         ends without any sentence-closing punctuation.
      3. The combined text would be ≤ 400 chars.
    This approach intentionally avoids merging intentionally short paragraphs
    that are stylistic choices by the publisher.
    """
    if first.get("type") != "paragraph" or second.get("type") != "paragraph":
        return False

    raw_first  = _strip_html_tags(first.get("text",  "")).strip()
    raw_second = _strip_html_tags(second.get("text", "")).strip()

    if not raw_first or not raw_second:
        return False

    last_char  = raw_first[-1] if raw_first else ''
    first_len  = len(raw_first)
    second_len = len(raw_second)

    # Rule 3: combined limit
    if first_len + second_len + 1 > 400:
        return False

    # Rule 2a: explicit continuation
    if last_char in _CONTINUATION_ENDERS:
        return True

    # Rule 2b: both very short and no sentence closer
    if first_len <= 60 and second_len <= 60 and last_char not in _SENTENCE_ENDERS:
        return True

    return False


def _merge_paragraphs(blocks: list[dict]) -> tuple[list[dict], int]:
    """
    Merge adjacent paragraph fragments that clearly belong together.
    Returns (merged_blocks, merge_count).
    """
    if len(blocks) < 2:
        return blocks, 0

    result  = []
    merges  = 0
    i       = 0

    while i < len(blocks):
        block = blocks[i]

        if block.get("type") == "paragraph" and i + 1 < len(blocks):
            # Look ahead: try to merge consecutive eligible paragraphs
            merged_text  = block.get("text", "")
            j            = i + 1
            merge_count  = 0

            while j < len(blocks) and merge_count < 2:  # limit: merge at most 3 into 1
                candidate = blocks[j]
                # Build a temporary dict with current merged text for the check
                current = {"type": "paragraph", "text": merged_text}
                if _can_merge(current, candidate):
                    merged_text += " " + candidate.get("text", "")
                    j           += 1
                    merge_count += 1
                    merges      += 1
                else:
                    break

            result.append({"type": "paragraph", "text": merged_text})
            i = j
        else:
            result.append(block)
            i += 1

    return result, merges


# ── E. Quality gate ───────────────────────────────────────────────────────────

def run(blocks: list[dict], source_domain: str = "") -> Optional[list[dict]]:
    """
    Run all cleanup sub-passes and apply the final quality gate.

    Returns cleaned blocks, or None if the content is too sparse to be
    a real article.
    """
    if not blocks:
        return None

    # A. Navigation block filter
    blocks = [b for b in blocks if not _is_navigation_block(b, source_domain=source_domain)]

    # B. Garbage block removal
    blocks = [b for b in blocks if not _is_garbage_block(b)]

    # B2. Drop trivially short text blocks (< 3 chars)
    cleaned = []
    for block in blocks:
        btype = block.get("type")
        if btype in ("paragraph", "heading", "quote"):
            if len(_strip_html_tags(block.get("text", "")).strip()) < 3:
                continue
        elif btype == "list":
            items = [it for it in block.get("items", []) if len(_strip_html_tags(it).strip()) >= 3]
            if not items:
                continue
            block = {**block, "items": items}
        cleaned.append(block)
    blocks = cleaned

    # C. Deduplication
    blocks, _removed = _deduplicate(blocks)

    # D. Paragraph merging
    blocks, _merged = _merge_paragraphs(blocks)

    # F. Orphan UI heading removal (after all content is settled)
    blocks, _orphans = _remove_orphan_ui_headings(blocks)

    # E. Quality gate: substantive block count
    substantive = [b for b in blocks if b.get("type") in _TEXT_BLOCK_TYPES]
    if len(substantive) < 3:
        return None

    # E2. Quality gate: total word count (price/date blocks excluded)
    total_words = 0
    for block in blocks:
        if block.get("type") in _WORD_COUNT_TYPES:
            total_words += len(_strip_html_tags(block.get("text", "")).split())
        elif block.get("type") == "list":
            for item in block.get("items", []):
                total_words += len(_strip_html_tags(item).split())

    if total_words < 100:
        return None

    return blocks


def run_with_stats(blocks: list[dict], source_domain: str = "") -> tuple[Optional[list[dict]], dict]:
    """
    Same as run() but also returns a stats dict for logging.
    """
    if not blocks:
        return None, {"input_blocks": 0}

    input_count = len(blocks)

    # A. Navigation block filter
    after_nav = [b for b in blocks if not _is_navigation_block(b, source_domain=source_domain)]
    nav_removed = input_count - len(after_nav)

    # B. Garbage block removal
    after_garbage = [b for b in after_nav if not _is_garbage_block(b)]
    garbage_removed = len(after_nav) - len(after_garbage)

    # B2. Short blocks
    cleaned = []
    for block in after_garbage:
        btype = block.get("type")
        if btype in ("paragraph", "heading", "quote"):
            if len(_strip_html_tags(block.get("text", "")).strip()) < 3:
                continue
        elif btype == "list":
            items = [it for it in block.get("items", []) if len(_strip_html_tags(it).strip()) >= 3]
            if not items:
                continue
            block = {**block, "items": items}
        cleaned.append(block)
    after_short = cleaned

    # C. Deduplication
    after_dedup, dedup_removed = _deduplicate(after_short)

    # D. Paragraph merging
    after_merge, merges = _merge_paragraphs(after_dedup)

    # F. Orphan UI heading removal
    after_orphan, orphans_removed = _remove_orphan_ui_headings(after_merge)

    # E. Quality gate
    substantive = [b for b in after_orphan if b.get("type") in _TEXT_BLOCK_TYPES]
    total_words = sum(
        len(_strip_html_tags(b.get("text", "")).split())
        for b in after_orphan if b.get("type") in _WORD_COUNT_TYPES
    )
    total_words += sum(
        len(_strip_html_tags(it).split())
        for b in after_orphan if b.get("type") == "list"
        for it in b.get("items", [])
    )

    passed = len(substantive) >= 3 and total_words >= 100
    final  = after_orphan if passed else None

    # Count block types
    type_counts: dict[str, int] = {}
    for b in (after_orphan or []):
        t = b.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    stats = {
        "input_blocks":        input_count,
        "output_blocks":       len(final) if final else 0,
        "nav_removed":         nav_removed,
        "garbage_removed":     garbage_removed,
        "dedup_removed":       dedup_removed,
        "orphan_removed":      orphans_removed,
        "paragraphs_merged":   merges,
        "paragraphs":          type_counts.get("paragraph", 0),
        "headings":            type_counts.get("heading",   0),
        "images":              type_counts.get("image",     0),
        "lists":               type_counts.get("list",      0),
        "quotes":              type_counts.get("quote",     0),
        "tables":              type_counts.get("table",     0),
        "embeds":              type_counts.get("embed",     0),
        "prices":              type_counts.get("price",     0),
        "dates":               type_counts.get("date",      0),
        "total_words":         total_words,
        "quality_gate_passed": passed,
    }
    return final, stats


# ── F. Orphan UI heading removal ────────────────────────────────────────────────────

_ORPHAN_HEADING_TEXTS = frozenset({
    # Recommendations
    "related stories", "related articles", "related posts", "related content",
    "related reading", "more from us", "you may also like", "recommended for you",
    "recommended", "read next", "what to read next", "up next", "see also",
    "editor's picks", "editors picks", "most popular", "trending", "trending now",
    "popular", "latest", "latest news", "latest articles", "latest posts",
    "featured articles", "featured stories", "featured content",
    "industry announcements", "newsletters", "around the web",
    "people also read", "people also viewed", "people also liked",
    # Comments
    "comments", "leave a reply", "leave a comment", "post a comment",
    "add a comment", "join the discussion", "discussion",
    "be the first to comment", "responses",
    # Newsletter
    "newsletter", "subscribe", "subscribe now", "sign up", "get updates",
    "email alerts", "stay up to date", "never miss",
    # Social
    "share", "share this", "share this article", "follow us",
    # Navigation
    "navigation", "site navigation", "quick links", "our sites", "our brands",
    "more from our brands", "more from our network",
    # Author bio
    "about the author", "author bio", "author profile",
    "follow the author", "follow author", "more from the author",
    # Ads
    "advertisement", "sponsored", "sponsored content", "partner content",
    # Footer
    "footer",
})


def _remove_orphan_ui_headings(blocks: list[dict]) -> tuple[list[dict], int]:
    """
    Sub-pass F: Remove UI headings that are immediately followed by another
    heading (their body was already removed by earlier passes), or that are
    at the very end of the block list with no content after them.
    Only headings whose text matches _ORPHAN_HEADING_TEXTS are eligible.
    """
    result: list[dict] = []
    removed = 0
    i = 0

    while i < len(blocks):
        block = blocks[i]
        if block.get("type") == "heading":
            heading_text = _strip_html_tags(block.get("text", "")).lower().strip()
            if heading_text in _ORPHAN_HEADING_TEXTS:
                # Check next block (skip is it another heading or end of list)
                next_i = i + 1
                if next_i >= len(blocks) or blocks[next_i].get("type") == "heading":
                    removed += 1
                    i += 1
                    continue
        result.append(block)
        i += 1

    return result, removed
