import logging
import time
import random
import cloudscraper
import trafilatura
import markdown
from bs4 import BeautifulSoup

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

def scrape_article_content(url: str) -> str | None:
    """
    Given a URL, uses cloudscraper to download the HTML and trafilatura
    to extract the main article content (preserving headings, lists, and images).
    Converts the output from Markdown to semantic HTML.

    Includes a delay and extended timeout to handle slower pages and lazy-loaded assets.
    
    Returns the HTML content or None if extraction fails.
    """
    # ── Wait/Delay ─────────────────────────────────────────────
    # A small randomized delay before scraping helps avoid bot detection 
    # and allows some breathing room between requests.
    time.sleep(random.uniform(1.0, 3.0))

    try:
        # ── Request with Timeout ────────────────────────────────
        # Increased timeout to 30s to allow slower pages to respond fully.
        response = scraper.get(url, timeout=30)
        response.raise_for_status()

        html_source = response.text

        # ── Pre-process for Lazy Images ─────────────────────────
        # Many modern sites use 'data-src' or similar for lazy loading.
        # Since we are not using a headless browser to execute JS, we manually 
        # swap these attributes into 'src' so trafilatura can see them.
        try:
            soup = BeautifulSoup(html_source, "html.parser")
            fixed_images = 0
            for img in soup.find_all("img"):
                # Common lazy-load attributes
                for attr in ["data-src", "data-lazy-src", "data-original", "data-actualsrc"]:
                    if img.has_attr(attr):
                        val = img.get(attr)
                        if val and val.startswith("http"):
                            img["src"] = val
                            fixed_images += 1
                            break
            if fixed_images > 0:
                html_source = str(soup)
        except Exception as e:
            logger.debug(f"[Extractor] Pre-processing failed for {url}: {e}")
        
        # Extract markdown, preserving images and structural links
        extracted_md = trafilatura.extract(
            html_source,
            include_images=True,
            include_links=True,
            output_format="markdown",
            url=url
        )

        if not extracted_md or len(extracted_md) < 150:
            logger.debug(f"[Extractor] Trafilatura failed to extract full content from {url} or content is too short (maybe JS wall).")
            return None

        # Convert the markdown back to HTML so it fits into our content field elegantly.
        # We enable 'extra' for tables/definition lists, and 'nl2br' for breaks.
        html_content = markdown.markdown(extracted_md, extensions=['extra', 'nl2br'])
        
        return html_content

    except Exception as e:
        logger.warning(f"[Extractor] Could not extract content from {url}: {e}")
        return None
