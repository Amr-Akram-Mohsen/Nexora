import logging
import time
import random
import cloudscraper
import trafilatura
import markdown
from bs4 import BeautifulSoup
import json
logger = logging.getLogger(__name__)

# Shared scraper to reuse connections and bypass protections
scraper = cloudscraper.create_scraper()


def enhance_article_html(html: str) -> str:
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # ── Headings ─────────────────────────────
    for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        for el in soup.find_all(tag):
            classes = el.get("class", [])
            el["class"] = classes + ["article-full-text__heading"]

    # ── Paragraphs ───────────────────────────
    for p in soup.find_all("p"):
        if not p.text.strip():
            p.decompose()
            continue
        classes = p.get("class", [])
        p["class"] = classes + ["article-full-text__paragraph"]

    # ── Images ───────────────────────────────
    for img in soup.find_all("img"):
        classes = img.get("class", [])
        img["class"] = classes + ["article-full-text__image"]
        img["loading"] = "lazy"

    # ── Links ────────────────────────────────
    for a in soup.find_all("a"):
        classes = a.get("class", [])
        a["class"] = classes + ["article-full-text__link"]
        a["target"] = "_blank"
        a["rel"] = "noopener noreferrer nofollow"

    # ── Lists ────────────────────────────────
    for tag in ["ul", "ol"]:
        for el in soup.find_all(tag):
            classes = el.get("class", [])
            el["class"] = classes + ["article-full-text__list"]

    # ── List items ───────────────────────────
    for li in soup.find_all("li"):
        classes = li.get("class", [])
        li["class"] = classes + ["article-full-text__list-item"]

    # ── Blockquotes ──────────────────────────
    for bq in soup.find_all("blockquote"):
        classes = bq.get("class", [])
        bq["class"] = classes + ["article-full-text__quote"]

    # ── Code blocks ──────────────────────────
    for pre in soup.find_all("pre"):
        classes = pre.get("class", [])
        pre["class"] = classes + ["article-full-text__code-block"]

    for code in soup.find_all("code"):
        classes = code.get("class", [])
        code["class"] = classes + ["article-full-text__code"]

    # ── Tables (wrap for responsiveness) ─────
    for table in soup.find_all("table"):
        wrapper = soup.new_tag("div", **{"class": "article-full-text__table-wrapper"})
        table.wrap(wrapper)
        classes = table.get("class", [])
        table["class"] = classes + ["article-full-text__table"]

    return str(soup)

from playwright.sync_api import sync_playwright

def _scrape_with_playwright(url: str) -> str | None:
    """
    Renders a URL using a headless browser.
    Resilient: Attempts to use system-installed Chrome/Edge if Playwright's 
    dedicated Chromium is missing.
    """
    logger.info(f"[Extractor] 🛠️ Attempting headless render: {url}")
    try:
        with sync_playwright() as p:
            browser = None
            # Iteratively try available browsers to avoid download dependency
            for channel in [None, "chrome", "msedge"]:
                try:
                    browser = p.chromium.launch(headless=True, channel=channel)
                    if browser:
                        logger.debug(f"[Extractor] Browser launched using channel: {channel or 'default'}")
                        break
                except Exception:
                    continue
            
            if not browser:
                logger.error("[Extractor] No suitable browser found (Chromium/Chrome/Edge). Please run 'playwright install chromium'")
                return None

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Navigate and wait for basic load (much faster than networkidle)
            page.goto(url, timeout=25000, wait_until="load")
            
            # Simple scroll to trigger lazy elements
            page.evaluate("window.scrollTo(0, document.body.scrollHeight/3)")
            time.sleep(1.0)
            
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.warning(f"[Extractor] Playwright rendering failed/timed out for {url}: {e}")
        return None

def _extract_from_json_ld(html: str) -> str | None:
    """
    Search for JSON-LD metadata and extract articleBody.
    This works on many modern JS-heavy sites where the text is hidden in SEO tags.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                # JSON-LD can be a single object or a list
                items = data if isinstance(data, list) else [data]
                for item in items:
                    # Look for Article, BlogPosting, or NewsArticle types
                    if item.get("@type") in ["Article", "BlogPosting", "NewsArticle"]:
                        body = item.get("articleBody") or item.get("description")
                        if body and len(body) > 300:
                            # Convert plain text body to simple HTML paragraphs
                            paragraphs = body.split("\n\n")
                            return "".join([f'<p class="article-full-text__paragraph">{p.strip()}</p>' for p in paragraphs if p.strip()])
            except Exception:
                continue
    except Exception:
        pass
    return None

def scrape_article_content(url: str) -> str | None:
    """
    Hybrid Fetching Strategy:
    1. Try CloudScraper (Fast, static).
    2. If result looks like a JS placeholder or short -> Use Playwright (Slow, rendered).
    3. Clean with Trafilatura.
    4. Fallback to JSON-LD metadata if all else fails.
    """
    # Reduced delay for better throughput
    time.sleep(random.uniform(0.3, 0.8))
    html_source = None
    
    # --- Try CloudScraper first (The "Fast" route) ---
    try:
        response = scraper.get(url, timeout=12)
        if response.status_code == 200:
            html_source = response.text
    except Exception as e:
        logger.debug(f"[Extractor] CloudScraper failed for {url}: {e}")

    # --- Intelligent Fallback: Only use Playwright if truly needed ---
    needs_playwright = False
    if not html_source or len(html_source) < 3000:
        needs_playwright = True
    elif "javascript" in html_source.lower() and ("enable" in html_source.lower() or "browser" in html_source.lower()):
        needs_playwright = True
        
    if needs_playwright:
        rendered_html = _scrape_with_playwright(url)
        if rendered_html:
            html_source = rendered_html

    if not html_source:
        return None

    # --- Pre-process for Lazy Images ---
    try:
        soup = BeautifulSoup(html_source, "html.parser")
        fixed = 0
        for img in soup.find_all("img"):
            # Deep lazy mapping (handle srcset and various data- attributes)
            lazy_attrs = ["data-src", "data-lazy-src", "data-original", "data-actualsrc", "srcset"]
            for attr in lazy_attrs:
                if img.has_attr(attr):
                    val = img.get(attr)
                    if isinstance(val, str):
                        # Simple split for srcset to take the first (main) URL
                        url_only = val.split(",")[0].split(" ")[0]
                        if url_only.startswith("http"):
                            img["src"] = url_only
                            fixed += 1
                            break
        if fixed > 0:
            html_source = str(soup)
    except Exception:
        pass

    # --- Trafilatura Cleaning ---
    try:
        extracted_md = trafilatura.extract(
            html_source,
            include_images=True,
            include_links=True,
            output_format="markdown",
            url=url
        )

        if extracted_md and len(extracted_md) > 250:
            # High quality content found
            html_content = markdown.markdown(extracted_md, extensions=['extra', 'nl2br'])
            return html_content
        
        # --- PHASE 4: JSON-LD Fallback (The "Last Resort") ---
        # If Trafilatura failed or gave back tiny content, try the hidden JSON schema
        json_ld_content = _extract_from_json_ld(html_source)
        if json_ld_content:
            logger.info(f"[Extractor] Fallback to JSON-LD success for: {url}")
            return json_ld_content

        return None

    except Exception as e:
        logger.warning(f"[Extractor] Trafilatura/Fallback Error for {url}: {e}")
        return None
