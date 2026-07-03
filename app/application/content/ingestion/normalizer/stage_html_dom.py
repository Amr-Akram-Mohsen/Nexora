"""
DOM-Level HTML Cleanup
----------------------
Removes entire UI components (newsletter widgets, cookie banners, 
related articles, sidebars) from raw HTML before it is converted to Markdown.
This prevents UI text from leaking into the block extraction pipeline.
"""
import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Elements to remove entirely (and their children)
_REMOVE_SELECTORS = [
    # Core non-content elements
    "script", "style", "noscript", "iframe", "form", "button", "input", "select", "textarea",
    "nav", "header", "footer", "aside",

    # Cookie & Privacy SDKs
    "[id*='onetrust']", "[id*='cookie']", "[id*='consent']",
    "[class*='cookie']", "[class*='consent']",

    # UI popups & modals
    "[id*='notification']", "[class*='notification']",
    "[role='dialog']", "[role='alertdialog']",
    "[class*='popup']", "[class*='modal']", "[class*='overlay']",

    # Newsletter / Subscribe
    "[class*='newsletter']", "[class*='subscribe']", "[id*='subscribe']", "[id*='newsletter']",

    # Social / Sharing
    "[class*='social']", "[class*='share']", "[id*='social']", "[id*='share']",

    # Comments
    "[class*='comment']", "[id*='comment']", "[class*='disqus']", "[id*='disqus']",

    # Related / Recommended / Promotional
    "[class*='related']", "[class*='recommended']", "[class*='promo']",
    "[class*='ad-']", "[class*='sponsor']", "[class*='trending']", "[class*='popular']",

    # Author bios / Sidebars / Widgets
    "[class*='author-bio']", "[class*='author-card']",
    "[class*='sidebar']", "[class*='widget']",
]

def run(html: str, source_domain: str | None = None) -> str:
    if not html or not html.strip():
        return ""

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.warning(f"Failed to parse HTML for DOM cleanup: {e}")
        return html

    # 1. Remove unwanted elements
    for selector in _REMOVE_SELECTORS:
        for tag in soup.select(selector):
            tag.decompose()

    # 1.5 Remove promotional wrappers specific to the site (e.g., Support MacDailyNews, MacDailyNews Take)
    if source_domain:
        _remove_promotional_site_wrappers(soup, source_domain)

    # 2. Fix images wrapped in empty links: <a href=\"img.jpg\"><img src=\"img.jpg\"></a> -> <img src=\"img.jpg\">
    for a_tag in soup.find_all("a"):
        if a_tag.find("img") and len(a_tag.contents) == 1:
            a_tag.unwrap()
            
    # 3. Remove empty links that just clutter things: <a href="..."></a>
    for a_tag in soup.find_all("a"):
        if not a_tag.get_text(strip=True) and not a_tag.find("img"):
            a_tag.decompose()

    # 4. Clean up inline image credit captions like (Image credit: Future)
    for cap in soup.find_all(["figcaption", "p", "div", "span"]):
        text = cap.get_text(strip=True)
        if re.search(r'^\(?(?:Image|Photo)\s+credit:.*?\)?$', text, re.IGNORECASE) or \
           re.search(r'^\(?(?:Photo|Image)\s+by:.*?\)?$', text, re.IGNORECASE):
            cap.decompose()

    # Also clean within larger text blocks (e.g. if the credit is just appended)
    credit_pattern = re.compile(r'\(?(?:Image|Photo)\s+(?:credit|by):.*?\)?', re.IGNORECASE)
    for text_node in soup.find_all(string=credit_pattern):
        new_text = credit_pattern.sub('', text_node)
        text_node.replace_with(new_text)

    return str(soup)

def _remove_promotional_site_wrappers(soup: BeautifulSoup, source_domain: str):
    import urllib.parse
    
    # Extract base site name, e.g., www.macdailynews.com -> macdailynews
    site_name = source_domain.lower().replace("www.", "")
    if "." in site_name:
        site_name = site_name.split(".")[0]

    promo_patterns = [
        re.compile(fr'support\s+{re.escape(site_name)}', re.IGNORECASE),
        re.compile(fr'subscribe\s+to\s+{re.escape(site_name)}', re.IGNORECASE),
        re.compile(fr'{re.escape(site_name)}\s+take:', re.IGNORECASE),
        re.compile(r'support\s+(?:our\s+)?(?:journalism|work)', re.IGNORECASE),
    ]

    # 1.6 Remove promotional wrappers specific to the site
    for tag in soup.find_all(["p", "div", "section", "aside"]):
        text = tag.get_text(strip=True)
        if not text:
            continue
        
        # If the block contains promotional text for the site, remove it entirely
        is_promo = any(p.search(text) for p in promo_patterns)
        if is_promo:
            tag.decompose()
            continue

        # Also check for Substack/Support links that signify a promotional wrapper
        # We check the raw html of the tag to see if it has internal promo links
        a_tags = tag.find_all("a")
        for a in a_tags:
            href = a.get("href", "").lower()
            if site_name in href and not a.find("img"):
                if len(text) < 250 and ("subscribe" in text.lower() or "support" in text.lower()):
                    tag.decompose()
                    break

    # 1.7 Safely unwrap all remaining internal links (keep the text, remove the URL)
    # This prevents internal site navigation/promos from polluting the DB, but safely
    # preserves the text of legitimate headings, lists, and paragraphs.
    for a in soup.find_all("a"):
        href = a.get("href", "").lower()
        if site_name in href and not a.find("img"):
            a.unwrap()

