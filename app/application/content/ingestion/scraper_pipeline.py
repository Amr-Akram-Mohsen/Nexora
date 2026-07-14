"""
Scraper Pipeline
-----------------
Fetches clean article HTML and Text via the Diffbot extraction API.
"""
import os
import time
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)


def fetch_and_clean_diffbot(url: str, hero_image_url: str | None = None, api_key: str | None = None) -> dict:
    """
    Fetch *url* via Diffbot.
    Retries up to 3 times on HTTP 429 (rate-limited) responses.
    Raises ValueError if all attempts are exhausted or Diffbot returns no article objects.
    """
    if not api_key:
        try:
            api_key = current_app.config.get("DIFFBOT_API_KEY")
        except RuntimeError:
            api_key = os.environ.get("DIFFBOT_API_KEY")

    if not api_key:
        raise ValueError("DIFFBOT_API_KEY is missing from environment")

    params = {
        "token": api_key,
        "url": url,
        "fields": "tags,categories,meta,authors,siteName,summary,html",
        "timeout": 60000,  # 60s render timeout for Diffbot
        "scroll": "slow",
        "naturalLanguage": "summary",
    }

    response = None
    for attempt in range(5):
        response = requests.get(
            "https://api.diffbot.com/v3/article",
            params=params,
            timeout=65,
        )
        if response.status_code == 429:
            retry_str = response.headers.get("Retry-After")
            try:
                retry_after = int(retry_str) if retry_str else 3 * (2 ** attempt)
            except (ValueError, TypeError):
                # Diffbot might send non-standard formats like "0 days, 00:00:07"
                retry_after = 3 * (2 ** attempt)
                
            logger.warning(
                "[diffbot] 429 Too Many Requests (attempt %d/5) — sleeping %ds before retry",
                attempt + 1,
                retry_after
            )
            time.sleep(retry_after)
            continue
        response.raise_for_status()
        break
    else:
        # All 5 attempts returned 429 — surface the error cleanly
        raise ValueError("Diffbot returned 429 Too Many Requests after 5 retries")

    data = response.json()
    objects = data.get("objects", [])
    if not objects:
        raise ValueError("No article objects returned by Diffbot")

    article = objects[0]

    raw_html = article.get("html", "")
    logger.debug("[diffbot] html=%s  url=%s", "present" if raw_html else "absent", url[:80])

    # Map Diffbot 'tags' directly to 'concepts' so relationships logic handles them identically
    if "tags" in article:
        article["concepts"] = article["tags"]

    logger.debug(
        "[diffbot] url=%s images=%d",
        url[:80],
        len(article.get("images", [])),
    )

    # Note: Discussions (comments) are intentionally ignored.
    return {
        "content_text":     article.get("text", ""),
        "content_html":     raw_html,
        "metadata":         article,  # Pass full diffbot payload to be mapped upstream
        "images":           article.get("images", []),  # Diffbot's image array
        "ingestion_method": "diffbot",
    }
