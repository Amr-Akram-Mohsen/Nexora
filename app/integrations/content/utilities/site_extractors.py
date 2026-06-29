import logging
from bs4 import BeautifulSoup
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

def extract_hypebeast(soup: BeautifulSoup, url: str) -> Optional[str]:
    """Extracts article content specifically for Hypebeast."""
    # Hypebeast usually stores content in .post-body or .post-content
    container = soup.find("div", class_="post-body") or soup.find("div", class_="post-content")
    if container:
        # Hypebeast places ads inside content, we can strip them
        for ad in container.find_all("div", class_="ad-container"):
            ad.decompose()
        return str(container)
    return None

def extract_theverge(soup: BeautifulSoup, url: str) -> Optional[str]:
    """Extracts article content specifically for The Verge."""
    # The Verge uses specific block components
    container = soup.find("div", class_="duet--article--article-body-component") or soup.find("div", class_="c-entry-content")
    if container:
        return str(container)
    return None

def extract_bloomberg(soup: BeautifulSoup, url: str) -> Optional[str]:
    """Extracts article content specifically for Bloomberg."""
    container = soup.find("div", class_="body-copy") or soup.find("div", class_="article-body__content")
    if container:
        return str(container)
    return None

# Registry of site-specific extractors
SITE_EXTRACTORS: Dict[str, Callable[[BeautifulSoup, str], Optional[str]]] = {
    "hypebeast.com": extract_hypebeast,
    "theverge.com": extract_theverge,
    "bloomberg.com": extract_bloomberg,
}

def apply_site_specific_extractor(html_source: str, url: str) -> Optional[str]:
    """
    Checks if a custom extractor exists for the domain and applies it.
    Returns the extracted HTML string if successful, else None.
    """
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        extractor = SITE_EXTRACTORS.get(domain)
        if not extractor:
            # Fallback for subdomains if main domain is registered
            for registered_domain, ext in SITE_EXTRACTORS.items():
                if domain.endswith("." + registered_domain):
                    extractor = ext
                    break

        if extractor:
            logger.debug(f"[SCRAPE] Using site-specific extractor for {domain}")
            soup = BeautifulSoup(html_source, "html.parser")
            return extractor(soup, url)
            
        return None
    except Exception as e:
        logger.debug(f"[SCRAPE] Site-specific extractor failed for {url}: {e}")
        return None
