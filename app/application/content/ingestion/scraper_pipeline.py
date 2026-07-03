"""
Scraper Pipeline
-----------------
Fetches article content via Firecrawl or Jina AI Reader and runs the full
normalizer pipeline to produce clean `content_markdown` and `content_blocks`.

Public functions:
    fetch_and_clean_firecrawl(url)  → dict
    fetch_and_clean_jina(url)       → dict
    scrape_and_ingest_article(...)  → (article, status)
"""
import os
import logging
import requests
from datetime import datetime
from app.shared.dto.ingestion import EnrichedItemDTO
from app.application.content.ingestion.article_ingestion import ingest_article
from app.application.content.ingestion.normalizer import normalize_markdown
from app.application.content.ingestion.normalizer.stage_2_junk_removal import (
    FIRECRAWL_WAIT_FOR_MS,
    FIRECRAWL_TIMEOUT_MS,
    JINA_TIMEOUT_SEC,
)
import dateutil.parser
import trafilatura
from app.application.content.ingestion.normalizer import stage_html_dom

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Firecrawl
# ---------------------------------------------------------------------------

def fetch_and_clean_firecrawl(url: str, hero_image_url: str | None = None) -> dict:
    """
    Fetch *url* via Firecrawl (markdown + html + metadata) and run the
    full normalizer pipeline.

    Returns:
        {
            content_markdown: str,
            content_blocks:   list | None,
            content_html:     str,
            metadata:         dict,
            extracted_images: list[str],
            content_source:   "firecrawl",
        }
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY is missing from environment")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "url":               url,
        "formats":           ["markdown", "html"],
        "onlyMainContent":   True,
        "waitFor":           FIRECRAWL_WAIT_FOR_MS,
        "timeout":           FIRECRAWL_TIMEOUT_MS,
        "removeBase64Images": True,
        "excludeTags": [
            "nav", "header", "footer", "aside",
            "script", "style", "form", "noscript",
            "[class*='ad']", "[class*='sponsor']",
            "[class*='promo']", "[class*='cookie']",
            "[class*='newsletter']", "[class*='subscribe']",
            "[class*='social']", "[class*='share']",
            "[id*='comment']", "[class*='comment']",
            "[class*='related']", "[class*='recommended']",
        ],
    }

    response = requests.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers=headers,
        json=payload,
        timeout=max(120, FIRECRAWL_TIMEOUT_MS // 1000 + 30),
    )
    response.raise_for_status()
    data = response.json().get("data", {})

    raw_markdown = data.get("markdown", "")
    raw_html     = data.get("html",     "")
    metadata     = data.get("metadata", {})

    # DOM-level cleanup before markdown processing
    clean_html = stage_html_dom.run(raw_html, source_domain=url)
    
    # Try to extract clean markdown from the cleaned HTML using trafilatura
    # This prevents UI components from turning into markdown in the first place
    extracted_md = trafilatura.extract(
        clean_html,
        include_links=True,
        include_images=True,
        include_formatting=True,
        include_tables=True
    )
    
    # Fallback to firecrawl markdown if trafilatura fails to extract
    if extracted_md and len(extracted_md.strip()) > 100:
        markdown_to_process = extracted_md
    else:
        markdown_to_process = raw_markdown

    # Run the full normalizer pipeline
    normalized = normalize_markdown(markdown_to_process, source_url=url, hero_image_url=hero_image_url)
    stats      = normalized.get("stats", {})

    logger.debug(
        "[firecrawl] url=%s  blocks=%d  paragraphs=%d  images=%d  words=%d  gate=%s",
        url[:80],
        stats.get("output_blocks", 0),
        stats.get("paragraphs", 0),
        stats.get("images", 0),
        stats.get("total_words", 0),
        "PASS" if stats.get("quality_gate_passed") else "FAIL",
    )

    return {
        "content_markdown": normalized["content_markdown"],
        "content_blocks":   normalized["content_blocks"],
        "content_html":     raw_html,
        "metadata":         metadata,
        "extracted_images": normalized["extracted_images"],
        "content_source":   "firecrawl",
    }


# ---------------------------------------------------------------------------
# Jina AI Reader
# ---------------------------------------------------------------------------

def fetch_and_clean_jina(url: str, hero_image_url: str | None = None) -> dict:
    """
    Fetch *url* via Jina AI Reader (markdown) and run the full normalizer
    pipeline.

    Returns:
        {
            content_markdown: str,
            content_blocks:   list | None,
            content_html:     str,       # Jina returns only markdown; we store it twice
            metadata:         dict,
            extracted_images: list[str],
            content_source:   "jina",
        }
    """
    api_key = os.environ.get("JINA_AI_API_KEY")
    if not api_key:
        raise ValueError("JINA_AI_API_KEY is missing from environment")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept":         "application/json",
        "X-Return-Format": "markdown",
        "X-No-Cache":     "true",
        # Ask Jina to remove navigation/ads before returning markdown
        "X-Remove-Selector": "nav, header, footer, aside, form, [class*='ad'], [class*='social'], [class*='share'], [class*='comment'], [class*='newsletter'], [class*='cookie']",
    }

    response = requests.get(
        f"https://r.jina.ai/{url}",
        headers=headers,
        timeout=JINA_TIMEOUT_SEC,
    )
    response.raise_for_status()
    data = response.json().get("data", {})

    raw_markdown = data.get("content", "")
    metadata = {
        "title":       data.get("title",       ""),
        "description": data.get("description", ""),
        "url":         data.get("url",          url),
    }

    normalized = normalize_markdown(raw_markdown, source_url=url, hero_image_url=hero_image_url)
    stats      = normalized.get("stats", {})

    logger.debug(
        "[jina] url=%s  blocks=%d  paragraphs=%d  images=%d  words=%d  gate=%s",
        url[:80],
        stats.get("output_blocks", 0),
        stats.get("paragraphs", 0),
        stats.get("images", 0),
        stats.get("total_words", 0),
        "PASS" if stats.get("quality_gate_passed") else "FAIL",
    )

    return {
        "content_markdown": normalized["content_markdown"],
        "content_blocks":   normalized["content_blocks"],
        "content_html":     normalized["content_markdown"],  # Jina only returns markdown
        "metadata":         metadata,
        "extracted_images": normalized["extracted_images"],
        "content_source":   "jina",
    }


