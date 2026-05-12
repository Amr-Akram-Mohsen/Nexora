# app/integrations/content/newsapi.py
import logging
import requests
from flask import current_app
from app.integrations.exceptions import PipelineQuotaExceededError
from app.shared.utils.logging import log_integration_start, log_integration_success, log_integration_error

logger = logging.getLogger(__name__)

_NAME = "newsapi"


def fetch_newsapi_query(q_obj: dict, **kwargs) -> list[dict]:
    """
    Pure fetcher for NewsAPI.
    Focuses only on API request and returning raw data.
    Always returns a list (never None).
    """
    api_key = current_app.config.get("NEWS_API_KEY")
    if not api_key:
        logger.warning("[INTEGRATION][%s] skipped  reason=no_api_key", _NAME)
        return []

    q_text = q_obj.get("query", "")
    logger.debug("[INTEGRATION][%s] start  query=%s", _NAME, q_text)

    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q":        q_text,
                "language": "en",
                "sortBy":   "publishedAt",
                "pageSize": 80,
                "apiKey":   api_key,
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
            # Map NewsAPI specific fields to standard DTO fields
            a["image_url"] = a.get("urlToImage")
            raw_items.append(RawItemDTO(**a))

        logger.debug("[INTEGRATION][%s] success  items=%d  query=%s", _NAME, len(raw_items), q_text)
        return raw_items

    except requests.exceptions.RequestException as e:
        if hasattr(e, "response") and e.response is not None and (e.response.status_code == 403 or e.response.status_code == 429):
            raise PipelineQuotaExceededError("NewsAPI quota exhausted")
        from app.integrations.exceptions import PipelineTransientError
        raise PipelineTransientError(f"NewsAPI network error: {str(e)}") from e
    except Exception as e:
        from app.integrations.exceptions import PipelineFatalError
        raise PipelineFatalError(f"NewsAPI unexpected error: {str(e)}") from e
