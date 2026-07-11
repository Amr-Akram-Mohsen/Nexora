"""
Scraper Pipeline
-----------------
Fetches clean article HTML and Text via the Diffbot extraction API.
"""
import os
import logging
import re
import requests
from flask import current_app
logger = logging.getLogger(__name__)

def fetch_and_clean_diffbot(url: str, hero_image_url: str | None = None, api_key: str | None = None) -> dict:
    """
    Fetch *url* via Diffbot.
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
        "fields": "tags,categories,meta,authors,siteName,summary",
        "timeout": 60000, # 60s render timeout for Diffbot
        "scroll": "slow",
        "naturalLanguage": "summary"
    }

    # Diffbot extraction
    response = requests.get(
        "https://api.diffbot.com/v3/article",
        params=params,
        timeout=65, # Requests timeout slightly higher than Diffbot's internal limit
    )
    response.raise_for_status()
    data = response.json()
    objects = data.get("objects", [])
    if not objects:
        raise ValueError("No article objects returned by Diffbot")
        
    article = objects[0]

    raw_html = article.get("html", "")
    
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
        "metadata":         article, # Pass full diffbot payload to be mapped upstream
        "images":           article.get("images", []), # Diffbot's image array
        "ingestion_method": "diffbot",
    }
