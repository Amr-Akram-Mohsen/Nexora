from flask import current_app
from .quality import score_content_quality
from app.shared.utils.logging import (
    log_scrape_start,
    log_scrape_success,
    log_scrape_error,
)
import logging

logger = logging.getLogger(__name__)


def _extract_diffbot(url: str, api_key: str) -> dict | None:
    try:
        import requests

        api_url = "https://api.diffbot.com/v3/article"
        params = {"token": api_key, "url": url}
        response = requests.get(api_url, params=params, timeout=2.5)
        response.raise_for_status()
        data = response.json()

        if "objects" in data and len(data["objects"]) > 0:
            article = data["objects"][0]
            content_html = article.get("html", "")
            content_text = article.get("text", "")

            if not content_html and not content_text:
                return None

            word_count = len(content_text.split()) if content_text else 0
            quality = score_content_quality(content_html, content_text)

            # Extract image (Diffbot returns a list of images)
            images = article.get("images", [])
            image_url = (
                images[0].get("url") if images and isinstance(images, list) else None
            )

            return {
                "content_html": content_html,
                "content_text": content_text,
                "image_url": image_url,
                "word_count": word_count,
                "quality_score": quality,
                "source": "diffbot",
            }
    except Exception as e:
        log_scrape_error(logger, url, f"diffbot_failed: {e}")
    return None


def extract_with_apis(url: str) -> dict | None:
    """
    Try external extractor APIs (Diffbot, Mercury, etc.).
    Returns normalized output or None if all fail / no keys.
    """
    try:
        # Check Diffbot
        diffbot_key = current_app.config.get("DIFFBOT_API_KEY")
        if diffbot_key:
            log_scrape_start(logger, url)
            result = _extract_diffbot(url, diffbot_key)
            if result:
                log_scrape_success(
                    logger, url, words=result.get("word_count", 0), source="diffbot"
                )
                return result

    except RuntimeError as e:
        # Outside app context or config unavailable (e.g., during tests)
        logger.debug("[SCRAPE] skipped  reason=no_app_context  url=%s  err=%s", url, e)

    return None
