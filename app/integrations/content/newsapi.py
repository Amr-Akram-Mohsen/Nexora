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
    log_integration_start(logger, _NAME, query=q_text)

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

        log_integration_success(logger, _NAME, items=len(raw_items), query=q_text)
        return raw_items

    except requests.exceptions.RequestException as e:
        if hasattr(e, "response") and e.response is not None and e.response.status_code == 403:
            raise PipelineQuotaExceededError("NewsAPI Quota Exceeded")
        log_integration_error(logger, _NAME, e, query=q_text)
        return []
    except Exception as e:
        log_integration_error(logger, _NAME, e, query=q_text, exc_info=True)
        return []
