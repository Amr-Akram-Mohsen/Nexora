"""
app/integrations/content/extract_article_content.py

Production-grade article scraping and HTML normalization pipeline.

Pipeline:
  1. Fetch HTML  — CloudScraper (fast) → Playwright (JS fallback)
  2. Pre-process — Fix lazy images before passing to extractor
  3. Extract     — Trafilatura XML → JSON-LD fallback
  4. Normalize   — Convert XML tags → clean HTML
  5. Clean       — Remove artifacts, ghost whitespace, junk nodes
  6. Enhance     — Apply article-full-text__* class system
  7. Sanitize    — bleach (in cleaner.py, after this returns)
"""

import json
import logging
import random
import re
import time
from urllib.parse import urljoin, urlparse

import cloudscraper
import trafilatura
from bs4 import BeautifulSoup, NavigableString, Comment
from app.shared.utils.logging import log_scrape_start, log_scrape_success, log_scrape_error

logger = logging.getLogger(__name__)

# ── Shared CloudScraper session ──────────────────────────────────────────────
_scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)

# ── Tags whose whitespace-only text children are noise ───────────────────────
_STRUCTURAL_TAGS = frozenset({
    "table", "thead", "tbody", "tfoot", "tr", "colgroup", "col",
    "ul", "ol", "dl", "figure", "div", "section", "article", "nav",
    "header", "footer", "aside", "main",
})

# ── Tags that carry no semantic value and can be unwrapped ───────────────────
_UNWRAP_TAGS = frozenset({"span", "font", "center"})

# ── Attributes to strip entirely (non-useful metadata / tracking) ────────────
_STRIP_ATTRS = re.compile(
    r"^(data-(?!src$|lazy-src$|original$)|"
    r"style|onclick|onload|onerror|aria-hidden|"
    r"tabindex|data-track|data-analytics)$",
    re.I,
)

# ── Separator patterns: lines that are purely decorative ─────────────────────
_SEP_RE = re.compile(r"^[\s\-=_*•·~#|]{4,}$")

# ── Long-run whitespace between tags ─────────────────────────────────────────
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_MULTI_SPACE_RE   = re.compile(r"[^\S\r\n]{2,}")  # collapses spaces/tabs but not newlines


# ────────────────────────────────────────────────────────────────────────────
# SECTION 1 — HTML Cleaning & Normalization
# ────────────────────────────────────────────────────────────────────────────

def _strip_noise_from_soup(soup: BeautifulSoup) -> None:
    """In-place: remove comments, tracking attrs, and unwrap meaningless wrappers."""
    # Remove HTML comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # Strip noisy attributes across all tags
    for tag in soup.find_all(True):
        attrs_to_remove = [a for a in list(tag.attrs) if _STRIP_ATTRS.match(a)]
        for attr in attrs_to_remove:
            del tag[attr]

    # Unwrap semantically empty inline wrappers (preserves inner content)
    for tag in soup.find_all(_UNWRAP_TAGS):
        tag.unwrap()


def _remove_ghost_whitespace(soup: BeautifulSoup) -> None:
    """In-place: delete whitespace-only NavigableString nodes inside structural tags."""
    for tag in soup.find_all(_STRUCTURAL_TAGS):
        for child in list(tag.children):
            if isinstance(child, NavigableString) and not child.strip():
                child.extract()


def _collapse_internal_whitespace(soup: BeautifulSoup) -> None:
    """
    In-place: Collapse multiple spaces/newlines into a single space within 
    structural elements like tables and divs to keep the HTML clean and tight.
    """
    for tag in soup.find_all(["table", "thead", "tbody", "tr", "td", "th", "div", "ul", "ol", "li"]):
        for child in tag.children:
            if isinstance(child, NavigableString):
                # Replace all whitespace (including newlines) with a single space
                collapsed = re.sub(r"\s+", " ", child.string)
                child.replace_with(collapsed)


def _trim_all_text_nodes(soup: BeautifulSoup) -> None:
    """In-place: strip leading/trailing whitespace from every text node (except pre/code)."""
    for node in soup.find_all(string=True):
        parent = node.parent
        if parent and parent.name in ("pre", "code", "textarea"):
            continue
        stripped = node.strip()
        if stripped != node:
            node.replace_with(stripped)


def _remove_separator_elements(soup: BeautifulSoup) -> None:
    """In-place: delete elements whose text is purely a visual separator."""
    for tag in soup.find_all(["p", "div", "span", "hr"]):
        text = tag.get_text(strip=True)
        if _SEP_RE.match(text):
            tag.decompose()


def _normalize_images(soup: BeautifulSoup, base_url: str = "") -> None:
    """In-place: resolve lazy-load attrs → src, remove broken images."""
    lazy_candidates = (
        "data-src", "data-lazy-src", "data-original",
        "data-actualsrc", "data-srcset", "srcset",
    )
    for img in soup.find_all("img"):
        # Resolve lazy src
        resolved = False
        for attr in lazy_candidates:
            val = img.get(attr, "")
            if not val:
                continue
            # srcset: take the first URL (highest priority)
            candidate = val.split(",")[0].split()[0]
            if candidate.startswith("http") or candidate.startswith("//"):
                img["src"] = candidate if candidate.startswith("http") else "https:" + candidate
                resolved = True
                break

        src = img.get("src", "")
        # Resolve relative URLs
        if src and not src.startswith("http") and base_url:
            img["src"] = urljoin(base_url, src)
            src = img["src"]

        # Remove clearly broken images
        if not src or src.startswith("data:") or len(src) < 10:
            img.decompose()
            continue

        # Ensure lazy loading
        img["loading"] = "lazy"
        img.attrs = {k: v for k, v in img.attrs.items() if k in ("src", "alt", "width", "height", "loading", "class")}


def _normalize_links(soup: BeautifulSoup) -> None:
    """In-place: apply safe attributes and strip javascript: hrefs."""
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if not href or href.startswith("javascript:") or href.startswith("#"):
            a.unwrap()
            continue
        a.attrs = {"href": href, "target": "_blank", "rel": "noopener noreferrer nofollow"}


def _prune_empty_nodes(soup: BeautifulSoup) -> None:
    """
    In-place: handle empty/near-empty block elements.
    - Pure separators → delete
    - Empty structural containers (table/ul) → mark, keep in DOM
    - Truly empty paragraphs → delete (no content value)
    """
    # Clean empty paragraphs aggressively
    for p in soup.find_all("p"):
        txt = p.get_text(strip=True)
        if not txt:
            p.decompose()

    # Mark (but keep) empty tables/lists — they may be layout placeholders
    for tag_name in ("table", "ul", "ol"):
        for el in soup.find_all(tag_name):
            if not el.get_text(strip=True):
                existing = el.get("class", [])
                el["class"] = existing + ["article-full-text__empty-structure"]


def clean_html(html: str, base_url: str = "") -> str:
    """
    Full HTML normalization pass.
    Returns cleaned, compact HTML with no ghost whitespace or junk nodes.
    """
    if not html:
        return ""

    # Regex passes (cheap, before BS4 parse)
    html = _MULTI_NEWLINE_RE.sub("\n\n", html)
    html = _MULTI_SPACE_RE.sub(" ", html)
    # Kill long separator strings in raw text
    html = re.sub(r"[-=_]{5,}", "", html)

    soup = BeautifulSoup(html, "html.parser")

    _strip_noise_from_soup(soup)
    _normalize_images(soup, base_url)
    _normalize_links(soup)
    _remove_ghost_whitespace(soup)
    _collapse_internal_whitespace(soup) # NEW
    _remove_separator_elements(soup)
    _trim_all_text_nodes(soup)
    _prune_empty_nodes(soup)
    # Final pass to ensure structural tags are clean
    _remove_ghost_whitespace(soup)

    clean_str = str(soup)
    
    # Post-BS4 Aggressive Regex cleanup
    clean_str = re.sub(r'>\s+<', '><', clean_str) # Strip whitespace between tags
    clean_str = re.sub(r'\n\s*\n', '\n', clean_str) # Collapse empty lines
    return clean_str.strip()


# ────────────────────────────────────────────────────────────────────────────
# SECTION 2 — HTML Class Enhancement
# ────────────────────────────────────────────────────────────────────────────

_HEADING_CLASS = "article-full-text__heading"
_CLASS_MAP = {
    "p":          "article-full-text__paragraph",
    "img":        "article-full-text__image",
    "ul":         "article-full-text__list",
    "ol":         "article-full-text__list",
    "li":         "article-full-text__list-item",
    "blockquote": "article-full-text__blockquote",
    "pre":        "article-full-text__code-block",
    "code":       "article-full-text__code",
    "a":          "article-full-text__link",
    "figure":     "article-full-text__figure",
    "figcaption": "article-full-text__caption",
}


def enhance_article_html(html: str) -> str:
    """
    Apply the article-full-text__* class system to cleaned HTML.
    Tables are wrapped for responsiveness.
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Headings
    for level in ("h1", "h2", "h3", "h4", "h5", "h6"):
        for el in soup.find_all(level):
            _add_class(el, _HEADING_CLASS)
            _add_class(el, f"article-full-text__heading--{level}")

    # Standard element classes
    for tag_name, css_class in _CLASS_MAP.items():
        for el in soup.find_all(tag_name):
            _add_class(el, css_class)

    # Tables: wrap for horizontal scroll if not already wrapped
    for table in soup.find_all("table"):
        if table.parent and "article-full-text__table-wrapper" in (table.parent.get("class") or []):
            continue  # already wrapped
        wrapper = soup.new_tag("div")
        wrapper["class"] = ["article-full-text__table-wrapper"]
        table.wrap(wrapper)
        _add_class(table, "article-full-text__table")

    return str(soup)


def _add_class(tag, css_class: str) -> None:
    """Safely add a class to a tag without duplicating."""
    existing = tag.get("class") or []
    if css_class not in existing:
        tag["class"] = existing + [css_class]


# ────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Fetching
# ────────────────────────────────────────────────────────────────────────────

def _fetch_static(url: str) -> str | None:
    """Try CloudScraper first (fast, handles Cloudflare)."""
    try:
        resp = _scraper.get(url, timeout=12)
        if resp.status_code == 200 and len(resp.text) > 2000:
            return resp.text
    except Exception as e:
        logger.debug("[SCRAPE] cloudscraper_failed  url=%s  err=%s", url, e)
    return None


def _is_js_wall(html: str) -> bool:
    """Detect JS-rendered-only pages that need Playwright."""
    if len(html) < 3000:
        return True
    lower = html.lower()
    js_indicators = (
        ("javascript" in lower and ("enable" in lower or "disabled" in lower)),
        ("noscript" in lower and len(html) < 8000),
        ("<body" in lower and html.lower().count("<p") < 3),
    )
    return any(js_indicators)


def _fetch_rendered(url: str) -> str | None:
    """Playwright headless rendering — only used when static fetch is insufficient."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log_scrape_error(logger, url, "playwright_not_installed")
        return None

    logger.debug("[SCRAPE] headless_rendering  url=%s", url)
    try:
        with sync_playwright() as p:
            browser = None
            for channel in (None, "chrome", "msedge"):
                try:
                    browser = p.chromium.launch(headless=True, channel=channel)
                    break
                except Exception:
                    continue

            if not browser:
                log_scrape_error(logger, url, "no_browser_available")
                return None

            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = ctx.new_page()
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            time.sleep(0.8)
            result = page.content()
            browser.close()
            return result
    except Exception as e:
        # Collapse the (potentially multi-line) exception message to a single log line
        short_msg = str(e).split("\n")[0]
        log_scrape_error(logger, url, f"playwright_failed: {short_msg}")
        return None


# ────────────────────────────────────────────────────────────────────────────
# SECTION 4 — Content Extraction
# ────────────────────────────────────────────────────────────────────────────

def _extract_via_trafilatura(html_source: str, url: str) -> str | None:
    """
    Use Trafilatura in XML mode for structured output, then convert to HTML.
    XML mode preserves bold, italic, lists better than plain HTML mode.
    """
    try:
        xml = trafilatura.extract(
            html_source,
            include_images=True,
            include_links=True,
            include_formatting=True,
            include_tables=True,
            output_format="xml",
            url=url,
            no_fallback=False,
            favor_precision=False,
            favor_recall=True,
        )
        if not xml or len(xml) < 200:
            return None

        # Convert Trafilatura XML vocabulary → standard HTML
        html = (
            xml
            .replace("<list>",   "<ul>").replace("</list>",   "</ul>")
            .replace("<item>",   "<li>").replace("</item>",   "</li>")
            .replace("<main>",   "<div>").replace("</main>",   "</div>")
            .replace("<head>",   "").replace("</head>",   "")  # strip any stray xml head
        )
        return html
    except Exception as e:
        logger.debug("[Extractor] Trafilatura error for %s: %s", url, e)
        return None


def _extract_via_json_ld(html_source: str) -> str | None:
    """
    Fallback: parse JSON-LD structured data to get articleBody.
    Works on many news sites that expose full text in SEO metadata.
    """
    try:
        soup = BeautifulSoup(html_source, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Article", "BlogPosting", "NewsArticle", "WebPage"):
                        body = item.get("articleBody") or item.get("description") or ""
                        if len(body) > 300:
                            paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
                            return "".join(f"<p>{p}</p>" for p in paragraphs)
            except Exception:
                continue
    except Exception:
        pass
    return None


# ────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Public Entry Point
# ────────────────────────────────────────────────────────────────────────────

def scrape_article_content(url: str) -> str | None:
    """
    Full pipeline:
      1. Fetch (static → rendered fallback)
      2. Pre-process lazy images on raw HTML
      3. Extract with Trafilatura
      4. Fallback to JSON-LD
      5. Clean + normalize + enhance classes

    Returns enhanced HTML string, or None if extraction failed.
    """
    # Polite delay
    time.sleep(random.uniform(0.3, 0.9))
    log_scrape_start(logger, url)

    # ── Step 1: Fetch ────────────────────────────────────────────
    html_source = _fetch_static(url)
    if not html_source or _is_js_wall(html_source):
        rendered = _fetch_rendered(url)
        if rendered:
            html_source = rendered

    if not html_source:
        log_scrape_error(logger, url, "fetch_failed")
        return None

    # ── Step 2: Pre-process lazy images on the raw source ────────
    try:
        raw_soup = BeautifulSoup(html_source, "html.parser")
        _normalize_images(raw_soup, base_url=url)
        html_source = str(raw_soup)
    except Exception:
        pass  # Non-critical; Trafilatura will still work on original

    # ── Step 3: Extract structured content ───────────────────────
    extracted = _extract_via_trafilatura(html_source, url)

    if not extracted or len(extracted.strip()) < 250:
        extracted = _extract_via_json_ld(html_source)
        if extracted:
            logger.debug("[SCRAPE] json_ld_fallback_success  url=%s", url)

    if not extracted or len(extracted.strip()) < 150:
        log_scrape_error(logger, url, "insufficient_content")
        return None

    # ── Step 4: Clean, normalize, enhance ────────────────────────
    cleaned  = clean_html(extracted, base_url=url)
    enhanced = enhance_article_html(cleaned)

    if enhanced and enhanced.strip():
        word_count = len(re.sub(r'<[^>]+>', '', enhanced).split())
        log_scrape_success(logger, url, words=word_count, source="trafilatura_or_jsonld")
        return enhanced
    
    log_scrape_error(logger, url, "empty_result_after_cleaning")
    return None
