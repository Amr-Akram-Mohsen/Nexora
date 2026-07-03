"""
Stage 4: Content Block Parser
-------------------------------
Converts clean Markdown into a structured list of content blocks.

Block types (all publisher-agnostic):
  heading   — {"type": "heading",   "level": 1-6, "text": "..."}
  paragraph — {"type": "paragraph", "text": "..."}
  image     — {"type": "image",     "url": "...", "alt": "...", "caption": null | "..."}
  quote     — {"type": "quote",     "text": "..."}
  list      — {"type": "list",      "ordered": bool, "items": [...]}
  code      — {"type": "code",      "language": "...", "text": "..."}
  table     — {"type": "table",     "rows": [[cell, ...], ...]}
  embed     — {"type": "embed",     "provider": "youtube"|"twitter"|..., "url": "..."}
  divider   — {"type": "divider"}

Design:
  - Line-by-line stateful parser (no heavy dependencies)
  - Accumulates multi-line constructs (lists, code blocks, tables)
  - Caption lines immediately following an image are attached to that image
  - Embed URLs on their own line produce embed blocks
  - Skips empty/whitespace-only content
"""
import re
from typing import Optional

# ── Structural block regexes ──────────────────────────────────────────────────
_HEADING_RE   = re.compile(r'^(#{1,6})\s+(.+)')
# Updated: handle both ![]() and ![alt]() — stage 1 may not always strip alt
_IMAGE_RE     = re.compile(r'^!\[([^\]]*)\]\(([^\)]+)\)\s*$')
_QUOTE_RE     = re.compile(r'^>\s*(.*)')
_UL_RE        = re.compile(r'^[\*\-\+]\s+(.+)')
_OL_RE        = re.compile(r'^\d+\.\s+(.+)')
_HR_RE        = re.compile(r'^(?:\*{3,}|-{3,}|_{3,})\s*$')
_CODE_FENCE   = re.compile(r'^```(\w*)')
_TABLE_ROW    = re.compile(r'^\|(.+)\|')
_TABLE_SEP    = re.compile(r'^\|[\s\|\-:]+\|')

# ── Inline formatting ─────────────────────────────────────────────────────────
_INLINE_LINK      = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
_INLINE_BOLD_AST  = re.compile(r'\*\*(.+?)\*\*')
_INLINE_BOLD_UND  = re.compile(r'__(.+?)__')
_INLINE_ITAL_AST  = re.compile(r'\*(.+?)\*')
_INLINE_ITAL_UND  = re.compile(r'(?<![\w])_(.+?)_(?![\w])')  # avoid matching mid-word underscores
_INLINE_CODE      = re.compile(r'`([^`]+)`')

# ── Embed detection ───────────────────────────────────────────────────────────
_EMBED_PATTERNS = [
    # YouTube
    (re.compile(r'https?://(?:www\.)?(?:youtube\.com/watch\?[^\s]*v=|youtu\.be/)[\w\-]+'), "youtube"),
    # Twitter / X
    (re.compile(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+'), "twitter"),
    # Instagram
    (re.compile(r'https?://(?:www\.)?instagram\.com/p/[\w\-]+'), "instagram"),
    # TikTok
    (re.compile(r'https?://(?:www\.)?tiktok\.com/@[\w.]+/video/\d+'), "tiktok"),
]

# ── UI headings to drop (never article structure) ─────────────────────────────
# Heading text that, when detected as a block, should be silently dropped
# instead of emitted. These are checked AFTER truncation in stage 2, to
# catch UI headings that appear mid-article (not at the end).
_UI_HEADING_TEXTS = frozenset({
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

# ── Price block detection ──────────────────────────────────────────────────────────────────────
_PRICE_CURRENCY_RE = re.compile(
    r'[\$\u00a3\u20ac\u00a5\u20b9][\d,]+(?:\.\d{1,2})?'   # $X.XX, £X, €X, etc.
    r'|\b\d+(?:\.\d{1,2})?\s*(?:USD|GBP|EUR|JPY|AUD|CAD)\b'
)

# ── Article-relevant date block detection ─────────────────────────────────────────────
# Only dates that are ARTICLE CONTENT (release dates, event dates, deadlines).
# Publisher metadata dates ("Published:", "Updated:", "First published") are
# removed in stage 2 before reaching here.
_ARTICLE_DATE_LABEL_RE = re.compile(r"""
    (?ix)
    ^
    (?:
        release\s*date|launch(?:es?|ed)?(?:\s*date)?|ship(?:s|ping|ped)?(?:\s*date)?|
        announce[ds]?(?:\s*date)?|available(?:\s+(?:on|from|in))?|
        expect[eds]?(?:\s*date)?|debut(?:s|ed)?|reveal[eds]?|unveil[eds]?|
        scheduled?(?:\s+(?:for|date))?|due(?:\s+(?:date|on|in))?|
        arrive[ds]?|goes?\s+on\s+sale|coming\s+(?:soon|in)|
        out(?:\s+(?:on|in|now))?|starts?(?:\s+(?:on|in))?|
        start(?:\s+date)?|end(?:\s+date)?|deadline|event(?:\s+date)?
    )
    \s*:?\s*
""", re.VERBOSE | re.IGNORECASE)

_DATE_VALUE_RE = re.compile(r"""
    (?ix)
    (?:
        Q[1-4]\s*(?:20\d\d|19\d\d)                          # Q1 2026
        |(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|
           Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|
           Dec(?:ember)?)\s+\d{0,2},?\s*(?:20\d\d|19\d\d)   # March 15, 2026
        |\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(?:20\d\d|19\d\d)
        |(?:Spring|Summer|Fall|Winter|Autumn)\s+(?:20\d\d|19\d\d)  # Fall 2025
        |(?:Early|Mid|Late)\s+(?:20\d\d|19\d\d)             # Early 2026
        |TBA|TBD|Coming\s+Soon
    )
""", re.VERBOSE | re.IGNORECASE)

# ── Caption heuristics ────────────────────────────────────────────────────────
# A line qualifies as a caption if it:
#   - Is short (raw char count ≤ 200)
#   - Is not blank
#   - Is not a structural marker (heading, list, quote, HR, code fence, table)
#   - Is not itself an image
_CAPTION_MAX_LEN = 200
_STRUCT_STARTS   = ('#', '>', '*', '-', '+', '|', '`', '~')


def _is_caption_line(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > _CAPTION_MAX_LEN:
        return False
    if s[0] in _STRUCT_STARTS:
        return False
    if _HEADING_RE.match(s) or _HR_RE.match(s) or _IMAGE_RE.match(s):
        return False
    if s[0].isdigit() and _OL_RE.match(s):
        return False
    return True


# ── Source domain helpers ─────────────────────────────────────────────────────

def _url_is_source_domain(url: str, source_domain: str) -> bool:
    """Return True if *url* belongs to *source_domain* (handles www. variants)."""
    if not source_domain:
        return False
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host == source_domain or host.endswith("." + source_domain)
    except Exception:
        return False


def _parse_inline_markdown(text: str, source_domain: str = "") -> str:
    """
    Convert basic inline markdown (links, bold, italic, inline code) to HTML
    tags so the frontend can render them safely without marked.js.

    If a link points to the source_domain, the link text is preserved but
    the anchor tag is dropped (keeping readable prose without site navigation).
    """
    # 1. Inline code (do first so we don't alter code contents)
    text = _INLINE_CODE.sub(r'<code>\1</code>', text)

    # 2. Links
    def link_repl(match):
        label = match.group(1)
        url   = match.group(2)
        if _url_is_source_domain(url, source_domain):
            return label  # keep the readable label, drop the navigation link
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'

    text = _INLINE_LINK.sub(link_repl, text)

    # 3. Bold (both ** and __ variants) before italic
    text = _INLINE_BOLD_AST.sub(r'<strong>\1</strong>', text)
    text = _INLINE_BOLD_UND.sub(r'<strong>\1</strong>', text)

    # 4. Italic (both * and _ variants)
    text = _INLINE_ITAL_AST.sub(r'<em>\1</em>', text)
    text = _INLINE_ITAL_UND.sub(r'<em>\1</em>', text)

    # 5. Clean up extra whitespace
    text = re.sub(r' {2,}', ' ', text).strip()
    return text


def _is_price_dominant(raw_text: str) -> bool:
    """
    Return True if this text is primarily price/currency data with little prose.
    Used to reclassify paragraphs as 'price' blocks.
    Example: '**$101.00** | $60.60 sale **$1,900.00** | $1,330.00 sale'
    """
    clean = re.sub(r'<[^>]+>', '', raw_text).strip()
    if not clean:
        return False
    # Must contain at least one currency amount
    if not _PRICE_CURRENCY_RE.search(clean):
        return False
    # Strip price-related tokens to see how much prose is left
    residue = clean
    residue = _PRICE_CURRENCY_RE.sub(' ', residue)
    residue = re.sub(r'\d+(?:\.\d{1,2})?\s*%(?:\s+off)?', ' ', residue)
    residue = re.sub(
        r'\b(?:sale|off|was|now|save|saving|deal|discount|price|vs\.?|each|per|from|to)\b',
        ' ', residue, flags=re.I
    )
    residue = re.sub(r'[|/\-\u2013\u2014•·,()]+', ' ', residue)
    residue = re.sub(r'\s+', ' ', residue).strip()
    # Count remaining real words (>=3 chars, alphabetic)
    real_words = [w for w in residue.split() if len(w) >= 3 and w.isalpha()]
    return len(real_words) < 4


def _is_article_date(clean_text: str, n_lines: int) -> bool:
    """
    Return True if this paragraph is an article-relevant date annotation
    (e.g. 'Release date: March 15, 2026', 'Available: Q1 2026').

    Only considers single-line, short paragraphs with a recognized date label.
    Publisher metadata dates ('Published:', 'Updated:') are removed in stage 2.
    """
    if n_lines != 1:
        return False
    clean = re.sub(r'<[^>]+>', '', clean_text).strip()
    if len(clean) > 100:
        return False
    return bool(_ARTICLE_DATE_LABEL_RE.match(clean)) and bool(_DATE_VALUE_RE.search(clean))


def _classify_paragraph_type(text: str, n_lines: int) -> str:
    """Determine the semantic block type for a paragraph."""
    if _is_price_dominant(text):
        return "price"
    if _is_article_date(text, n_lines):
        return "date"
    return "paragraph"


def _detect_embed(line: str) -> Optional[dict]:
    """
    If *line* is a bare embed URL (possibly wrapped in markdown link syntax),
    return an embed block dict or None.
    """
    stripped = line.strip()
    # Try to extract a bare URL (could be raw URL or a markdown link)
    bare_url = stripped
    link_match = re.match(r'^\[.*?\]\((https?://[^\)]+)\)$', stripped)
    if link_match:
        bare_url = link_match.group(1)

    for pattern, provider in _EMBED_PATTERNS:
        m = pattern.search(bare_url)
        if m:
            url = m.group(0)
            return {"type": "embed", "provider": provider, "url": url}
    return None


def run(md: str, approved_images: set[str], source_domain: str = "") -> list[dict]:
    """Parse *md* into a list of content blocks."""
    lines  = md.splitlines()
    blocks: list[dict] = []
    i = 0

    while i < len(lines):
        line    = lines[i]
        stripped = line.strip()

        # Skip completely blank lines
        if not stripped:
            i += 1
            continue

        # ── Horizontal rule ───────────────────────────────────────────────
        if _HR_RE.match(stripped):
            blocks.append({"type": "divider"})
            i += 1
            continue

        # ── Fenced code block ─────────────────────────────────────────────
        fence_m = _CODE_FENCE.match(stripped)
        if fence_m:
            lang = fence_m.group(1) or ''
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            code_text = '\n'.join(code_lines).strip()
            if code_text:
                blocks.append({"type": "code", "language": lang, "text": code_text})
            continue

        # ── Table ─────────────────────────────────────────────────────────
        if _TABLE_ROW.match(stripped):
            table_rows = []
            while i < len(lines) and _TABLE_ROW.match(lines[i].strip()):
                row_line = lines[i].strip()
                if _TABLE_SEP.match(row_line):
                    i += 1
                    continue
                cells = [c.strip() for c in row_line.strip('|').split('|')]
                table_rows.append(cells)
                i += 1
            if len(table_rows) >= 2 and not _is_widget_table(table_rows):
                blocks.append({"type": "table", "rows": table_rows})
            continue

        # ── Heading ───────────────────────────────────────────────────────
        h_m = _HEADING_RE.match(stripped)
        if h_m:
            level = len(h_m.group(1))
            text  = _parse_inline_markdown(h_m.group(2).strip(), source_domain)
            # Drop headings that are publisher UI labels (navigation, related, etc.)
            if text and text.lower().strip() not in _UI_HEADING_TEXTS:
                blocks.append({"type": "heading", "level": level, "text": text})
            i += 1
            continue

        # ── Blockquote ────────────────────────────────────────────────────
        if stripped.startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                q_m = _QUOTE_RE.match(lines[i].strip())
                if q_m:
                    quote_lines.append(q_m.group(1).strip())
                i += 1
            text = _parse_inline_markdown(' '.join(q for q in quote_lines if q), source_domain)
            if text:
                blocks.append({"type": "quote", "text": text})
            continue

        # ── Unordered list ────────────────────────────────────────────────
        if _UL_RE.match(stripped):
            m        = _UL_RE.match(stripped)
            raw_item = m.group(1).strip()
            # Skip items that are pure source-domain links
            urls = re.findall(r'\[(?:[^\]]+)\]\((https?://[^\)]+)\)', raw_item)
            if urls and all(_url_is_source_domain(u, source_domain) for u in urls):
                i += 1
                continue
            parsed = _parse_inline_markdown(raw_item, source_domain)
            if parsed:
                if blocks and blocks[-1].get("type") == "list" and blocks[-1].get("ordered") is False:
                    blocks[-1]["items"].append(parsed)
                else:
                    blocks.append({"type": "list", "ordered": False, "items": [parsed]})
            i += 1
            continue

        # ── Ordered list ──────────────────────────────────────────────────
        if _OL_RE.match(stripped):
            m        = _OL_RE.match(stripped)
            raw_item = m.group(1).strip()
            urls     = re.findall(r'\[(?:[^\]]+)\]\((https?://[^\)]+)\)', raw_item)
            if urls and all(_url_is_source_domain(u, source_domain) for u in urls):
                i += 1
                continue
            parsed = _parse_inline_markdown(raw_item, source_domain)
            if parsed:
                if blocks and blocks[-1].get("type") == "list" and blocks[-1].get("ordered") is True:
                    blocks[-1]["items"].append(parsed)
                else:
                    blocks.append({"type": "list", "ordered": True, "items": [parsed]})
            i += 1
            continue

        # ── Standalone image line ─────────────────────────────────────────
        img_m = _IMAGE_RE.match(stripped)
        if img_m:
            alt_text = img_m.group(1).strip()
            url      = img_m.group(2).strip()
            if url in approved_images:
                block = {"type": "image", "url": url, "alt": alt_text or None, "caption": None}

                # ── Caption look-ahead ────────────────────────────────────
                i += 1
                # Skip blank lines between image and potential caption
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if i < len(lines) and _is_caption_line(lines[i]):
                    cap_raw = lines[i].strip()
                    # Reject if it's another image or embed
                    if not _IMAGE_RE.match(cap_raw) and not _detect_embed(cap_raw):
                        block["caption"] = _parse_inline_markdown(cap_raw, source_domain)
                        i += 1  # consume the caption line

                blocks.append(block)
            else:
                i += 1
            continue

        # ── Embed URLs on their own line ──────────────────────────────────
        embed = _detect_embed(stripped)
        if embed:
            blocks.append(embed)
            i += 1
            continue

        # ── Paragraph (everything else) ───────────────────────────────────
        # Accumulate consecutive non-blank, non-special lines into one paragraph.
        para_lines = []
        while i < len(lines):
            l = lines[i].strip()
            if not l:
                break
            # Stop if we hit a structural marker
            if (_HEADING_RE.match(l) or l.startswith('>') or
                    _UL_RE.match(l) or _OL_RE.match(l) or
                    _HR_RE.match(l) or _CODE_FENCE.match(l) or
                    _TABLE_ROW.match(l) or _IMAGE_RE.match(l)):
                break
            # Stop if line is a standalone embed URL
            if _detect_embed(l):
                break
            para_lines.append(l)
            i += 1

        text = _parse_inline_markdown(' '.join(para_lines).strip(), source_domain)
        if text:
            btype = _classify_paragraph_type(text, len(para_lines))
            blocks.append({"type": btype, "text": text})

    return blocks


def _is_widget_table(rows: list[list[str]]) -> bool:
    """
    Return True if the table looks like a sports score, statistics widget,
    or financial ticker — i.e. a layout/data widget, not editorial content.

    Heuristics:
      - Very small (2 rows, 1-2 cols) and all cells are short numbers → widget
      - Header row has only numeric or very short (<=6 char) cells → widget
    Keep tables that have a mix of text and numbers (spec sheets, comparisons, etc.)
    """
    if len(rows) < 2:
        return False

    # Only check small tables (score widgets are typically 2-5 rows, 2-4 cols)
    n_cols = len(rows[0])
    n_rows = len(rows)
    if n_rows > 8 or n_cols > 5:
        return False  # larger tables are more likely to be editorial

    # Count cells that are purely numeric (scores, stats)
    total_cells = sum(len(r) for r in rows)
    numeric_cells = sum(
        1 for row in rows for cell in row
        if re.match(r'^\d+(?:[\.:,]\d+)?[\%\+\-]?$', cell.strip())
    )
    if total_cells > 0 and numeric_cells / total_cells >= 0.7:
        return True

    return False
