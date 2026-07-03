"""
Stage 2: Junk Section Removal
-------------------------------
Detects and removes publisher page chrome that leaks into scraped Markdown.

Strategy:
  1. TRUNCATION — scan for footer/sidebar section headings and cut everything
     from that point onwards. The article text always comes before these.
  2. INLINE STRIPPING — remove specific patterns that appear inline or on
     their own line: nav links, social widgets, audio players, logos, ads.
  3. SOURCE-DOMAIN FILTERING — remove any line where every link points back
     to the article's own publisher domain (site navigation masquerading as
     article content).

All patterns are publisher-agnostic. They work on common HTML-rendered
Markdown conventions found across hundreds of publishers.
"""
import re

# ---------------------------------------------------------------------------
# Configurable extractor timeouts (imported by scraper_pipeline.py)
# ---------------------------------------------------------------------------
import os

FIRECRAWL_WAIT_FOR_MS  = int(os.environ.get("FIRECRAWL_WAIT_FOR_MS",  "8000"))
FIRECRAWL_TIMEOUT_MS   = int(os.environ.get("FIRECRAWL_TIMEOUT_MS",   "120000"))
JINA_TIMEOUT_SEC       = int(os.environ.get("JINA_TIMEOUT_SEC",       "90"))

# ---------------------------------------------------------------------------
# Truncation patterns — everything from the first match onward is discarded.
# Ordered: most-specific first so we cut at the earliest possible boundary.
# ---------------------------------------------------------------------------

_TRUNCATION_PATTERNS = [
    # ── Related / Recommended content ───────────────────────────────────
    r'(?im)^#{1,4}\s*Related\s+(?:Stories?|Posts?|Articles?|Content|News|Coverage|Topics?)',
    r'(?im)^#{1,4}\s*More\s+(?:Like\s+This|From\s+(?:Our\s+)?(?:Brands?|Network|Site|Us)?)',
    r'(?im)^#{1,4}\s*You\s+May\s+(?:Also\s+)?Like',
    r'(?im)^#{1,4}\s*Recommended\s+(?:For\s+You|Reading|Articles?|Stories?)',
    r'(?im)^#{1,4}\s*People\s+Also\s+(?:Read|Liked|Viewed)',
    r'(?im)^#{1,4}\s*Read\s+(?:Next|Also|More)',
    r'(?im)^#{1,4}\s*See\s+Also',
    r'(?im)^#{1,4}\s*(?:Editor\'?s?\s+)?Picks?',
    r'(?im)^#{1,4}\s*(?:Most\s+)?Popular(?:\s+(?:Articles?|Posts?|Stories?|Now))?',
    r'(?im)^#{1,4}\s*Trending(?:\s+(?:Now|Articles?|Stories?|Topics?))?',
    r'(?im)^#{1,4}\s*Latest\s+(?:Posts?|Articles?|News|Stories?)',
    r'(?im)^#{1,4}\s*What\s+to\s+Read\s+Next',
    r'(?im)^#{1,4}\s*Up\s+Next',
    # Bare text section dividers for related content
    r'(?im)^(?:Related\s+Stories?|Related\s+Articles?|More\s+From\s+Us)\s*$',
    r'(?im)^(?:You\s+May\s+Also\s+Like|Read\s+Next|See\s+Also)\s*$',
    r'(?im)^(?:Trending\s+Now|Most\s+Popular|Editor\'?s?\s+Picks?)\s*$',

    # ── Comments & discussion ────────────────────────────────────────────
    r'(?im)^#{1,4}\s*(?:Jump\s+to\s+)?Comments?',
    r'(?im)^#{1,4}\s*Leave\s+a\s+(?:Reply|Comment)',
    r'(?im)^#{1,4}\s*(?:Join\s+the\s+)?Discussion',
    r'(?im)^#{1,4}\s*(?:Community|Forum)',
    r'(?im)^#{1,4}\s*Be\s+the\s+[Ff]irst\s+to\s+[Cc]omment',
    r'(?im)^(?:Leave\s+a\s+Reply|Post\s+a\s+Comment|Add\s+a\s+Comment)\s*$',
    r'(?im)^\d+\s+[Cc]omments?\s*$',
    r'(?im)^(?:Loading\s+[Cc]omments?|No\s+[Cc]omments?\s+[Yy]et)\s*$',

    # ── Newsletter / subscription ────────────────────────────────────────
    r'(?im)^#{1,4}\s*Newsletter',
    r'(?im)^#{1,4}\s*Subscribe(?:\s+to\s+(?:our|the)\s+(?:newsletter|updates?))?',
    r'(?im)^#{1,4}\s*Sign\s+[Uu]p\s+(?:for|to)',
    r'(?im)^(?:Never\s+miss\s+an?\s+(?:update|story|article))\s*$',
    r'(?im)^(?:Subscribe\s+to\s+(?:our|the)\s+newsletter)\s*$',
    r'(?im)^(?:Sign\s+up\s+for\s+(?:our|the)\s+(?:daily|weekly)?)\s*newsletter',
    r'(?im)^(?:Get\s+the\s+(?:latest|best)\s+(?:news|stories?)\s+(?:in\s+your\s+inbox|delivered))',
    r'(?im)^Enter\s+your\s+email\s+address\s*$',

    # ── Author bio / social profile sections ─────────────────────────────
    r'(?im)^#{1,4}\s*About\s+the\s+[Aa]uthor',
    r'(?im)^#{1,4}\s*[Aa]uthor(?:\s+(?:Bio|Profile|Info|Information))?',
    r'(?im)^#{1,4}\s*(?:Written\s+by|By)\s+\w',
    r'(?im)^#{1,4}\s*(?:Follow|Connect\s+with)\s+(?:the\s+)?[Aa]uthor',
    r'(?im)^(?:About\s+the\s+Author)\s*$',
    r'(?im)^(?:Follow\s+(?:me|us)\s+on)\s*$',

    # ── Share / social ───────────────────────────────────────────────────
    r'(?im)^#{1,4}\s*Share\s+(?:this|the)\s+(?:article|story|post)',
    r'(?im)^#{1,4}\s*(?:Share|Spread\s+the\s+[Ww]ord)',

    # ── Publisher navigation / site footer ───────────────────────────────
    r'(?im)^#{1,4}\s*(?:Our\s+)?(?:Sites?|Brands?|Network|Publications?)',
    r'(?im)^#{1,4}\s*Footer',
    r'(?im)^#{1,4}\s*(?:Site\s+)?Navigation',
    r'(?im)^#{1,4}\s*(?:Quick\s+)?Links',
    r'(?im)^#{1,4}\s*Table\s+of\s+Contents',
    r'(?im)^#{1,4}\s*(?:In\s+[Tt]his\s+[Aa]rticle|Contents?)',

    # ── Copyright / legal ────────────────────────────────────────────────
    r'(?im)^\s*©\s*20\d\d',
    r'(?im)^All\s+[Rr]ights\s+[Rr]eserved',
    r'(?im)^Copyright\s+(?:\(c\)\s*)?20\d\d',

    # ── Paywall / membership ─────────────────────────────────────────────
    r'(?im)^#{1,4}\s*(?:Subscribe|Become\s+a\s+Member)\s+to\s+(?:Read|Continue|Access)',
    r'(?im)^(?:This\s+content\s+is\s+(?:for\s+)?(?:subscribers?|members?)\s+only)',
    r'(?im)^(?:You\'?ve?\s+(?:reached|hit)\s+(?:your|the)\s+(?:free\s+)?(?:article\s+)?limit)',
    r'(?im)^(?:Create\s+a\s+free\s+account\s+to\s+(?:read|continue|access))',
    r'(?im)^(?:Already\s+a\s+subscriber)',

    # ── Advertising signals ──────────────────────────────────────────────────
    r'(?im)^#{1,4}\s*(?:Sponsored\s+Content|Advertisement|Partner\s+Content)',
    r'(?im)^(?:SPONSORED|ADVERTISEMENT|PARTNER\s+CONTENT)\s*$',

    # ── Publisher-specific featured / industry sections ───────────────────
    r'(?im)^#{1,4}\s*Featured\s+(?:Articles?|Posts?|Stories?|Content)',
    r'(?im)^Featured\s+(?:Articles?|Posts?|Stories?)\s*$',
    r'(?im)^#{1,4}\s*Industry\s+Announcements?',
    r'(?im)^Industry\s+Announcements?\s*$',
    r'(?im)^#{1,4}\s*Newsletters?(?:\s*&\s*\w+)?\s*$',
    r'(?im)^Newsletters?\s*$',
    r'(?im)^#{1,4}\s*Around\s+the\s+Web',
    r'(?im)^#{1,4}\s*From\s+(?:Our\s+)?(?:Partners?|Sponsors?)',
    r'(?im)^#{1,4}\s*(?:Deals?|Shopping\s+Guides?|Product\s+Roundups?)',

    # ── Footer timestamp metadata (published / updated datelines) ─────────
    # These appear at the bottom of articles and duplicate Article.published_at
    r'(?im)^First\s+published\s+\w+\s+\d+',
    r'(?im)^(?:Last\s+)?(?:Updated?|Modified)\s+\w+\s+\d+,?\s*20\d\d',
    r'(?im)^(?:Published|Posted)\s+(?:on\s+)?\w+\s+\d+,?\s*20\d\d',

    # ── Inline article-continues separator ────────────────────────────────
    r'(?im)^[\-–—\s]*Article\s+continues?\s+below(?:\s+(?:advertisement|ad(?:vertisement)?|the\s+ad(?:vert)?))?[\-–—\s]*$',

    # ── Tags / filed under / category labels ─────────────────────────────
    r'(?im)^(?:Tags?|Filed\s+[Uu]nder|Labels?|Keywords?|Category|Categories)\s*:\s*.+$',
]

# ---------------------------------------------------------------------------
# Inline / line-level strip patterns — matched text is replaced with empty.
# ---------------------------------------------------------------------------

_STRIP_PATTERNS = [
    # ── Navigation buttons ───────────────────────────────────────────────
    r'(?i)\[\s*(?:Previous|Next|Share|Tweet|Print|Email|Read\s+More|Back|Continue\s+Reading)\s*\]\([^\)]+\)',

    # ── Social share links on their own line ─────────────────────────────
    r'(?im)^[\s\*]*\[\s*(?:Facebook|Twitter|X|Instagram|LinkedIn|Pinterest|YouTube|TikTok|WhatsApp|Telegram|Reddit|Flipboard)\s*\]\([^\)]+\)\s*$',

    # ── Audio player junk ────────────────────────────────────────────────
    r'(?i)Loading\s+Audio\s+Player.*?\n',
    r'(?i)In\s+Article\s+Audio\s+Player\n?',
    r'(?i)Listen\s+to\s+this\s+[Aa]rticle\n?',
    r'--:--\s*/\s*\n?\s*--:--',
    r'(?i)1x1\.25x1\.5x1\.75x2x2\.25x2\.5x2\.75x3x(?:0\.5x0\.75x)?',
    r'(?i)\b(?:0:00\s*/\s*0:00|00:00\s*/\s*00:00)\b',

    # ── Navigation menu lines ────────────────────────────────────────────
    r'(?im)^Menu\s*\[!?\[.*?\]\([^\)]+\)\]\([^\)]+\)\s*$',
    r'(?im)^Menu\s*$',
    r'(?i)\[random\]\([^\)]+\)',
    r'(?im)^\[Browse\\*\s*(?:all)?\s*[^\]]*\]\([^\)]+\)\s*$',
    r'(?im)^Browse\s+all\s+.*$',

    # ── Logo images ──────────────────────────────────────────────────────
    r'(?i)!\[[^\]]*logo[^\]]*\]\([^\)]+\)',
    r'(?i)!\[[^\]]*\]\([^)]*logo[^)]*\)',
    r'(?i)!\[[^\]]*\]\([^)]*favicon[^)]*\)',

    # ── Embedded widget banners ──────────────────────────────────────────
    r'(?i)!\[[^\]]*(?:instaread|podcast episode artwork|audio player)[^\]]*\]\([^\)]+\)',

    # ── Inline image-link gallery rows (related post thumbnails) ─────────
    r'(?im)^(?:!\[\]\([^\)]+\)\[[^\]]*\]\([^\)]+\)\s*){2,}$',
    r'(?im)^(?:\[!\[\]\([^\)]+\)\]\([^\)]+\)\s*){2,}$',

    # ── Cookie / GDPR banners ────────────────────────────────────────────
    r'(?im)^We\s+use\s+(?:cookies?|essential\s+cookies?).*?(?:Accept|Decline|OK)\s*$',
    r'(?im)^(?:Accept\s+(?:all\s+)?[Cc]ookies?|Decline\s+[Cc]ookies?|Manage\s+[Cc]ookies?)\s*$',
    r'(?im)^(?:This\s+(?:website|site)\s+uses?\s+cookies?).*?$',
    r'(?im)^(?:By\s+(?:clicking|continuing|using\s+this\s+site))\s+.*?(?:[Pp]rivacy\s+[Pp]olicy|[Cc]ookie\s+[Pp]olicy).*?$',
    r'(?im)^(?:Privacy\s+Settings?|Cookie\s+(?:Settings?|Preferences?))\s*$',

    # ── Advertisement / sponsored labels ─────────────────────────────────
    r'(?im)^[-–—]*\s*(?:Advertisement|Sponsored|Partner\s+Content|Paid\s+Content|Promoted)\s*[-–—]*\s*$',
    r'(?im)^\[\s*(?:Advertisement|Sponsored|Promoted|Partner\s+Content)\s*\]\s*$',

    # ── Loading / skeleton UI fragments ──────────────────────────────────
    r'(?im)^(?:Loading\s*\.{0,3}|Please\s+wait\s*\.{0,3}|Fetching\s+(?:data|content)\s*\.{0,3})\s*$',
    r'(?im)^(?:Skeleton\s+[Ll]oader|Placeholder)\s*$',

    # ── Reading progress / sticky UI labels ──────────────────────────────
    r'(?im)^(?:Back\s+to\s+[Tt]op|[\u2191\u25B2]\s*Back\s+to\s+[Tt]op|Scroll\s+to\s+[Tt]op)\s*$',
    r'(?im)^(?:Reading\s+[Pp]rogress:|Read:\s*\d+%)\s*$',

    # ── Emoji-only / decorative lines ────────────────────────────────────
    # (handled in stage 5 block-level; keep regex minimal here)

    # ── Instaread badge ──────────────────────────────────────────────────
    r'(?i)!\[[^\]]*instaread[^\]]*\]\([^\)]+\)',

    # ── Byline / dateline lines ──────────────────────────────────────────
    # e.g. "By Brett McKay • July 1, 2026" — author/date already in Article model
    r'(?im)^By\s+[\w][\w\s\.]+\s*[•·|,]\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^\n]{0,40}$',
    r'(?im)^[\w][\w\s\.]{3,30}\s*[•·]\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\w\s,]*20\d\d\s*$',
    r'(?im)^[\w][\w\s\.]{3,30}\s*\|\s+[\w][\w\s,\.]+\|\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^\n]{0,30}$',

    # ── Share / engagement count labels ─────────────────────────────────
    r'(?im)^\d+\s+(?:Shares?|Views?|Reads?|Likes?|Claps?)\s*$',

    # ── Print / Email article buttons ───────────────────────────────────
    r'(?im)^(?:Print|Email)\s+(?:this\s+)?(?:article|page|story)\s*$',

    # ── Gallery UI ───────────────────────────────────────────────────────
    r'(?im)^(?:Open\s+image\s+in\s+gallery|Expand\s+image|View\s+gallery|Load\s+more)\s*$',

    # ── Browser Notification UI ──────────────────────────────────────────
    r'(?im)^(?:Allow\s+notifications|Notifications?|Browser\s+preferences|Yes\s+please|Not\s+now)\s*$',

    # ── Community CTAs & Engagement Bait ─────────────────────────────────
    r'(?im)^(?:Join\s+us\s+on\s+Reddit|Leave\s+a\s+comment|Comments\s+below|Join\s+the\s+discussion|Share\s+your\s+thoughts)\s*$',
    r'(?im)^(?:Let\s+me\s+know\s+what\s+you\s+think|Let\s+me\s+know\s+in\s+the\s+comments)\s*$',
    r'(?im)^(?:Join\s+(?:our\s+)?(?:Discord|Telegram|WhatsApp|Facebook\s+Group)[^\]]*)\s*$',

    # ── Author Biography fragments ───────────────────────────────────────
    r'(?im)^(?:About\s+the\s+author|Author\s+bio|Staff\s+writer|Follow\s+author)\s*$',
    r'(?im)^.*has\s+been\s+writing.*$',
    r'(?im)^.*covers\s+.*$',
    r'(?im)^.*joined\s+.*$',

    # ── Standalone Image Credits ─────────────────────────────────────────
    r'(?im)^\(?(?:Image|Photo)\s+(?:credit|by):.*?\)?\s*$',
]

# Pre-compile strip patterns once at module load
_COMPILED_STRIP_PATTERNS = [re.compile(p) for p in _STRIP_PATTERNS]


def run(md: str, source_domain: str = "") -> str:
    truncated, truncation_trigger = _truncate_at_footer(md)
    stripped = _strip_inline_junk(truncated)
    if source_domain:
        stripped = _strip_source_domain_lines(stripped, source_domain)
    return stripped


# Expose truncation trigger for logging in __init__.py
def run_with_stats(md: str, source_domain: str = "") -> tuple[str, str | None]:
    """
    Same as run() but also returns the pattern that triggered truncation,
    or None if no truncation occurred.
    """
    truncated, trigger = _truncate_at_footer(md)
    stripped = _strip_inline_junk(truncated)
    if source_domain:
        stripped = _strip_source_domain_lines(stripped, source_domain)
    return stripped, trigger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate_at_footer(md: str) -> tuple[str, str | None]:
    earliest = len(md)
    trigger = None
    for pattern in _TRUNCATION_PATTERNS:
        match = re.search(pattern, md)
        if match and match.start() < earliest:
            earliest = match.start()
            trigger = pattern
    return md[:earliest], trigger


def _strip_inline_junk(md: str) -> str:
    for compiled in _COMPILED_STRIP_PATTERNS:
        md = compiled.sub('', md)
    return md


# Matches all markdown links on a line: [text](url)
_ALL_LINKS_RE = re.compile(r'\[([^\]]*)\]\((https?://[^\)]+)\)')


def _strip_source_domain_lines(md: str, source_domain: str) -> str:
    """
    Remove any line where EVERY hyperlink target belongs to the source domain.

    This catches site-navigation link lists that look like:
        * [How To](https://www.artofmanliness.com/skills/how-to/)
        * [Fitness](https://www.artofmanliness.com/health-fitness/)
    even when they contain readable text, because every URL leads back to
    the publisher's own site — i.e. they are internal navigation, not article
    content.
    """
    result_lines = []
    for line in md.splitlines():
        stripped = line.strip()
        if not stripped:
            result_lines.append(line)
            continue

        links = _ALL_LINKS_RE.findall(stripped)  # list of (text, url) tuples
        if not links:
            result_lines.append(line)
            continue

        # Check whether ALL links on this line point to the source domain
        all_source = all(
            _url_is_source_domain(url, source_domain)
            for _, url in links
        )
        if all_source:
            continue  # drop this line entirely

        result_lines.append(line)

    return '\n'.join(result_lines)


def _url_is_source_domain(url: str, source_domain: str) -> bool:
    """Return True if *url* belongs to *source_domain* (handles www. variants)."""
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host == source_domain or host.endswith("." + source_domain)
    except Exception:
        return False
