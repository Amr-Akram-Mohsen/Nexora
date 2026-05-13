# app/integrations/content/newsapi.py
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import current_app
from app.integrations.exceptions import PipelineQuotaExceededError
from app.shared.utils.logging import log_integration_start, log_integration_success, log_integration_error, log_integration_warning

logger = logging.getLogger(__name__)

_NAME = "newsapi"

def _get_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def fetch_newsapi_query(q_obj: dict, **kwargs) -> list[dict]:
    """
    Pure fetcher for NewsAPI.
    Focuses only on API request and returning raw data.
    Always returns a list (never None).
    """
    api_key = current_app.config.get("NEWS_API_KEY")
    if not api_key:
        log_integration_warning(logger, _NAME, reason="no_api_key")
        return []

    q_text = q_obj.get("query", "")
    log_integration_start(logger, _NAME, query=q_text)

    session = _get_session()
    try:
        resp = session.get(
            "https://newsapi.org/v2/everything",
            params={
                "q":        q_text,
                "language": "en",
                "sortBy":   "publishedAt",
                "pageSize": 80,
                "apiKey":   api_key,
            },
            timeout=(5, 15), # (connect, read) timeout
        )
        resp.raise_for_status()
        from app.shared.dto.ingestion import RawItemDTO

        articles = resp.json().get("articles", [])
        if not isinstance(articles, list):
            log_integration_warning(logger, _NAME, reason="unexpected_response_shape", query=q_text)
            articles = []

        raw_items = []
        for a in articles:
            if not isinstance(a, dict):
                continue
            # Map NewsAPI specific fields to standard DTO fields
            a["image_url"] = a.get("urlToImage")
            a["source_name"] = (a.get("source") or {}).get("name")
            raw_items.append(RawItemDTO(**a))

        log_integration_success(logger, _NAME, items=len(raw_items), query=q_text)
        return raw_items

    except requests.exceptions.RequestException as e:
        if hasattr(e, "response") and e.response is not None and (e.response.status_code == 403 or e.response.status_code == 429):
            log_integration_error(logger, _NAME, e, query=q_text)
            raise PipelineQuotaExceededError("NewsAPI quota exhausted")
        from app.integrations.exceptions import PipelineTransientError
        log_integration_error(logger, _NAME, e, query=q_text)
        raise PipelineTransientError(f"NewsAPI network error: {str(e)}") from e
    except Exception as e:
        from app.integrations.exceptions import PipelineFatalError
        log_integration_error(logger, _NAME, e, query=q_text)
        raise PipelineFatalError(f"NewsAPI unexpected error: {str(e)}") from e
