# app/integrations/content/article_utils/metadata.py
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def recover_article_metadata(url: str) -> dict:
    """
    Performs a lightweight fetch and parse to find OpenGraph and Canonical tags.
    """
    result = {
        "image_url": None,
        "canonical_url": None
    }
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        resp = requests.get(url, timeout=7, headers=headers)
        if resp.status_code != 200:
            return result

        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 1. Image Recovery
        og_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og_image and og_image.get("content"):
            result["image_url"] = og_image["content"]
        else:
            twitter_image = soup.find("meta", property="twitter:image") or soup.find("meta", attrs={"name": "twitter:image"})
            if twitter_image and twitter_image.get("content"):
                result["image_url"] = twitter_image["content"]

        # 2. Canonical URL Recovery
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            result["canonical_url"] = canonical["href"]

    except Exception as e:
        logger.debug("[METADATA] recovery_failed  url=%s  err=%s", url, e)
        
    return result

# Backward compatibility alias
def recover_og_image(url: str) -> str | None:
    return recover_article_metadata(url).get("image_url")
