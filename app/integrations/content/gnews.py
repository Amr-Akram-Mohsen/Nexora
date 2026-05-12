# app/integrations/content/gnews.py
import logging
import requests
from flask import current_app
from app.integrations.exceptions import PipelineQuotaExceededError
from app.shared.utils.logging import log_integration_start, log_integration_success, log_integration_error

logger = logging.getLogger(__name__)

_NAME = "gnews"

_ARABIC_CHARS = set("ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي")


def fetch_gnews_query(q_obj: dict, **kwargs) -> list[dict]:
    """
    Pure fetcher for GNews.
    Always returns a list (never None).
    """
    api_key = current_app.config.get("GNEWS_API_KEY")
    if not api_key:
        logger.warning("[INTEGRATION][%s] skipped  reason=no_api_key", _NAME)
        return []

    q_text = q_obj.get("query", "")
    # Sanitize: '&' in category names (e.g. "Niche & Artisanal") breaks GNews URL parsing
    q_text = q_text.replace(" & ", " and ").replace("&", "and")
    country = q_obj.get("region", "sa").lower()
    lang = "ar" if any(c in q_text for c in _ARABIC_CHARS) else "en"
    logger.debug("[INTEGRATION][%s] start  query=%s  country=%s  lang=%s", _NAME, q_text, country, lang)

    try:
        resp = requests.get(
            "https://gnews.io/api/v4/search",
            params={
                "q":       q_text,
                "lang":    lang,
                "country": country,
                "max":     50,
                "apikey":  api_key,
            },
            timeout=10,
        )
        resp.raise_for_status()

        from app.shared.dto.ingestion import RawItemDTO
        articles = resp.json().get("articles", [])
        if not isinstance(articles, list):
            logger.warning("[INTEGRATION][%s] unexpected response shape for query=%s", _NAME, q_text)
            articles = []

        raw_items = []
        for a in articles:
            if not isinstance(a, dict):
                continue
            a["image_url"] = a.get("image")
            a["region"] = country.upper()
            raw_items.append(RawItemDTO(**a))

        logger.debug("[INTEGRATION][%s] success  items=%d  query=%s", _NAME, len(raw_items), q_text)
        return raw_items

    except requests.exceptions.RequestException as e:
        if hasattr(e, "response") and e.response is not None and (e.response.status_code == 403 or e.response.status_code == 429):
            raise PipelineQuotaExceededError("GNews quota exhausted")
        from app.integrations.exceptions import PipelineTransientError
        raise PipelineTransientError(f"GNews network error: {str(e)}") from e
    except Exception as e:
        from app.integrations.exceptions import PipelineFatalError
        raise PipelineFatalError(f"GNews unexpected error: {str(e)}") from e
