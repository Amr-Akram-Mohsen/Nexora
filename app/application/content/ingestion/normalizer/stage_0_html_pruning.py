"""
Stage 0: Structural Block-Level Pruning
-----------------------------------------
Operates on raw markdown BEFORE any preprocessing. Removes entire multi-line
paragraph chunks that correspond to publisher UI containers:

  - Newsletter / subscription forms
  - Comment sections and reply widgets
  - Login / authentication prompts
  - Cookie / privacy consent banners
  - Social share widget blocks
  - Recommendation thumbnail grids
  - Author bio / profile card widgets
  - Pure navigation link menus (all links → same publisher domain)
  - Advertisement / sponsored content blocks

This stage works at the "paragraph chunk" level (blank-line-separated blocks).
It is conservative: a chunk is only erased when it clearly matches a structural
UI pattern AND contains fewer than 2 genuine editorial prose lines.

After chunk erasure, orphan headings (headings whose body was deleted, or
headings immediately followed by another heading) are removed if they match
known UI heading text.
"""
import re


# ---------------------------------------------------------------------------
# UI heading detector
# Matches heading text (including the leading # characters) against
# known publisher UI section labels.
# ---------------------------------------------------------------------------

_UI_HEADING_TEXT_RE = re.compile(r"""
    (?ix)
    ^
    \#{1,6}\s+
    (?:
        # Newsletter / subscription
        newsletter|subscribe(?:\s+now)?|subscription|
        sign[\s\-]?up(?:\s+(?:for|to))?|
        get\s+(?:updates?|the\s+(?:latest|newsletter|digest))|
        email\s+alerts?|daily\s+(?:newsletter|digest|email)|
        weekly\s+(?:newsletter|digest|email)|never\s+miss|
        join\s+(?:our|the)(?:\s+\w+)?\s+(?:newsletter|community)|
        stay\s+(?:up\s+to\s+date|informed|connected)|

        # Comments
        (?:jump\s+to\s+)?comments?|leave\s+a?\s+(?:reply|comment)|
        post\s+a?\s+comment|add\s+a?\s+comment|join\s+the\s+discussion|
        be\s+the\s+first(?:\s+to\s+comment)?|discussion|responses?|

        # Login / auth
        log[\s\-]?in|sign[\s\-]?in|create\s+(?:an?\s+)?account|
        register(?:\s+now)?|member(?:ship)?\s+(?:access|only|login)|
        continue\s+(?:reading|with)|unlock\s+(?:article|content)|
        already\s+(?:a\s+)?(?:subscriber|member)|

        # Cookie / privacy
        cookie\s+(?:policy|settings?|preferences?|notice)|
        privacy\s+(?:settings?|notice|center)|consent|gdpr|

        # Social / sharing
        share(?:\s+this)?(?:\s+article)?|follow\s+us|

        # Author bio/profile card
        about\s+the\s+author|author\s+(?:bio|profile|information?|info)|
        written\s+by|follow\s+(?:the\s+)?author|
        (?:more\s+)?from\s+the\s+author|latest\s+from\s+(?:the\s+)?author|

        # Ads / sponsored
        advertisement|sponsored(?:\s+content)?|partner\s+content|

        # Related / recommended
        related\s+(?:stories?|articles?|posts?|content|reading)|
        recommended(?:\s+for\s+you)?|you\s+may\s+(?:also\s+)?like|
        more\s+(?:from(?:\s+(?:us|our\s+\w+))?|like\s+this|stories?|articles?)|
        people\s+also\s+(?:read|viewed|liked)|what\s+to\s+read\s+next|
        up\s+next|editor(?:'?s?)?\s+picks?|(?:most\s+)?popular|
        trending(?:\s+now)?|latest\s+(?:posts?|news|articles?|stories?)|
        featured\s+(?:articles?|stories?|posts?|content)|
        industry\s+announcements?|

        # Navigation
        (?:site\s+)?navigation|quick\s+links?|our\s+(?:sites?|brands?)|

        # Donations / fundraising
        donat(?:e|ion|ing)|support\s+(?:us|our\s+journalism)|
        fund(?:raise|raiser)|

        # Polls / surveys
        poll|survey|quiz|take\s+our\s+(?:poll|survey|quiz)
    )
    \s*$
""", re.VERBOSE | re.IGNORECASE)

# ---------------------------------------------------------------------------
# Line-level signals
# ---------------------------------------------------------------------------

# Lines that look like form inputs / subscribe buttons
_FORM_LINE_PATTERNS = [
    re.compile(r'(?i)enter\s+your\s+email|your\s+email(?:\s+address)?|email\s+address'),
    re.compile(r'(?i)(?:your\s+)?(?:first|last)\s+name'),
    re.compile(r'(?im)^\[?\s*(?:subscribe|sign\s+up|submit|send|get\s+(?:updates?|access|started)|join\s+now)\s*\]?\s*(?:\([^)]+\))?\s*$'),
    re.compile(r'(?i)^\s*(?:already\s+(?:a\s+)?subscriber|manage\s+preferences?)\s*$'),
    re.compile(r'(?i)type\s+(?:here|your)'),
]

# Lines that are solely social platform share buttons / links
_SOCIAL_LINE_RE = re.compile(
    r'(?im)^\[?\s*(?:'
    r'facebook|twitter|x\b|instagram|linkedin|pinterest|youtube|tiktok|'
    r'whatsapp|telegram|reddit|flipboard|threads|snapchat|mastodon|'
    r'share|tweet|retweet|copy\s+link|email\s+this|print'
    r')\s*\]?(?:\([^)]*\))?\s*$'
)

# Linked thumbnail: [![](url)](url)  — recommendation card pattern
_LINKED_THUMB_RE = re.compile(r'^\s*\[!\[\]\([^)]+\)\]\([^)]+\)\s*$')

# All markdown links in a line
_ALL_MD_LINKS_RE = re.compile(r'\[([^\]]*)\]\((https?://[^)]+)\)')

# Genuine prose line heuristic — 6+ real words, not a heading/list/link/image
_WORD_RE = re.compile(r'\b[a-zA-Z]{3,}\b')

# Comment-section signal phrases (checked against full chunk text lowercased)
_COMMENT_SIGNALS = frozenset({
    'leave a reply', 'post a comment', 'add a comment',
    'be the first to comment', 'be the first to write a comment',
    'loading comments', 'no comments yet', 'join the discussion',
    'comment form', 'disqus', 'facebook comments',
    'your comment', 'submit comment', 'name (required)',
    'notify me of new comments', 'notify me of new posts',
})

# Cookie/privacy signal phrases
_COOKIE_SIGNALS = frozenset({
    'we use cookies', 'this site uses cookies', 'this website uses cookies',
    'by clicking accept', 'by continuing to use', 'by using this site',
    'manage cookies', 'accept cookies', 'decline cookies',
    'privacy settings', 'cookie settings', 'gdpr',
    'accept all cookies', 'reject all cookies',
})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(md: str, source_domain: str = "") -> str:
    """
    Remove publisher UI container blocks from raw markdown.
    Returns cleaned markdown with UI chunks and orphan headings removed.
    """
    if not md:
        return md

    chunks = _split_into_chunks(md)
    kept: list[list[str]] = []

    for chunk in chunks:
        if _chunk_is_ui_container(chunk, source_domain=source_domain):
            pass  # drop entire chunk
        else:
            kept.append(chunk)

    result = "\n\n".join("\n".join(chunk) for chunk in kept)
    result = _remove_orphan_headings(result)
    return result


# ---------------------------------------------------------------------------
# Chunk splitting
# ---------------------------------------------------------------------------

def _split_into_chunks(md: str) -> list[list[str]]:
    """Split markdown into paragraph chunks (separated by blank lines)."""
    chunks: list[list[str]] = []
    current: list[str] = []
    for line in md.splitlines():
        if not line.strip():
            if current:
                chunks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        chunks.append(current)
    return chunks


# ---------------------------------------------------------------------------
# Chunk classification
# ---------------------------------------------------------------------------

def _count_prose_lines(lines: list[str]) -> int:
    """Count lines that look like genuine editorial prose (6+ real words, no structural marker)."""
    count = 0
    for line in lines:
        s = line.strip()
        if not s:
            continue
        # Skip structural / non-prose lines
        if s[0] in ('#', '*', '-', '+', '>', '|', '`', '~', '!'):
            continue
        # Skip lines that are purely a markdown link
        links = _ALL_MD_LINKS_RE.findall(s)
        clean_of_links = _ALL_MD_LINKS_RE.sub(' ', s).strip()
        if links and len(clean_of_links) < 5:
            continue
        # Require 6+ real words
        real_words = _WORD_RE.findall(s)
        if len(real_words) >= 6:
            count += 1
    return count


def _chunk_is_ui_container(lines: list[str], source_domain: str = "") -> bool:
    """
    Return True if this chunk represents a publisher UI container and
    contains fewer than 2 genuine editorial prose lines.
    Conservative: keeps the chunk if it has real prose.
    """
    # Gate: 2+ prose lines → always keep
    prose_count = _count_prose_lines(lines)
    if prose_count >= 2:
        return False

    full_lower = "\n".join(lines).lower()

    has_ui_heading     = any(_UI_HEADING_TEXT_RE.match(l.strip()) for l in lines)
    form_count         = sum(1 for l in lines if _is_form_like_line(l.strip()))
    social_count       = sum(1 for l in lines if _SOCIAL_LINE_RE.match(l.strip()))
    linked_thumb_count = sum(1 for l in lines if _LINKED_THUMB_RE.match(l.strip()))
    comment_hits       = sum(1 for sig in _COMMENT_SIGNALS if sig in full_lower)
    cookie_hits        = sum(1 for sig in _COOKIE_SIGNALS  if sig in full_lower)

    # Newsletter / subscription form
    if has_ui_heading and form_count >= 1 and prose_count == 0:
        return True

    # Comment section
    if comment_hits >= 2 and prose_count == 0:
        return True

    # Cookie/privacy banner
    if cookie_hits >= 2 and prose_count == 0:
        return True

    # Social share widget (UI heading + social links, or 3+ bare social lines)
    if has_ui_heading and social_count >= 2:
        return True
    if social_count >= 3 and len(lines) <= 10 and prose_count == 0:
        return True

    # Recommendation / related grid: UI heading + multiple linked thumbnails
    if has_ui_heading and linked_thumb_count >= 2:
        return True

    # Pure linked thumbnail grid (≥3 recommendation cards with no prose)
    if linked_thumb_count >= 3 and prose_count == 0:
        return True

    # Source-domain pure navigation block
    if source_domain and _is_pure_source_nav(lines, source_domain) and prose_count == 0:
        return True

    return False


def _is_form_like_line(line: str) -> bool:
    return any(p.search(line) for p in _FORM_LINE_PATTERNS)


def _is_pure_source_nav(lines: list[str], source_domain: str) -> bool:
    """True if ≥75% of non-empty lines are markdown links all pointing to source_domain."""
    non_empty = [l for l in lines if l.strip()]
    if len(non_empty) < 2:
        return False
    source_link_lines = 0
    for line in non_empty:
        links = _ALL_MD_LINKS_RE.findall(line)
        if links and all(_url_is_source_domain(url, source_domain) for _, url in links):
            source_link_lines += 1
    return source_link_lines / len(non_empty) >= 0.75


def _url_is_source_domain(url: str, source_domain: str) -> bool:
    try:
        host = url.split('/')[2].lower()
        if host.startswith('www.'):
            host = host[4:]
        return host == source_domain or host.endswith('.' + source_domain)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Orphan heading removal
# ---------------------------------------------------------------------------

_HEADING_LINE_RE = re.compile(r'^(#{1,6})\s+(.+)$')


def _remove_orphan_headings(md: str) -> str:
    """
    Remove UI headings that are immediately followed by another heading
    or have no following content (their body was erased by the chunk pass).
    Only headings matching _UI_HEADING_TEXT_RE are eligible for removal.
    """
    lines = md.splitlines()
    result: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        h_m = _HEADING_LINE_RE.match(line.strip())

        if h_m and _UI_HEADING_TEXT_RE.match(line.strip()):
            # Find the next non-blank line
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            # Orphan: next content is another heading, or end of document
            if j >= len(lines) or _HEADING_LINE_RE.match(lines[j].strip()):
                i += 1
                continue  # skip this heading

        result.append(line)
        i += 1

    return "\n".join(result)
