# app/integrations/content/gnews.py
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import current_app
from app.integrations.exceptions import PipelineQuotaExceededError
from app.shared.utils.logging import log_integration_start, log_integration_success, log_integration_error, log_integration_warning

logger = logging.getLogger(__name__)

_NAME = "gnews"

_ARABIC_CHARS = set("ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي")
_session = None

def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": "Nexora Content Fetcher"
        })

        retries = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True
        )
        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=10,
            pool_maxsize=10,
        )
        _session.mount("https://", adapter)
    return _session

def fetch_gnews_query(q_obj: dict, **kwargs) -> list[dict]:
    """
    Pure fetcher for GNews.
    Always returns a list (never None).
    """
    api_key = current_app.config.get("GNEWS_API_KEY")
    if not api_key:
        log_integration_warning(logger, _NAME, reason="no_api_key")
        return []

    q_text = q_obj.get("query", "")
    # Sanitize: '&' in category names (e.g. "Niche & Artisanal") breaks GNews URL parsing
    q_text = q_text.replace(" & ", " and ").replace("&", "and")
    country = q_obj.get("region", "sa").lower()
    lang = "ar" if any(c in q_text for c in _ARABIC_CHARS) else "en"
    log_integration_start(logger, _NAME, query=q_text, country=country, lang=lang)

    session = _get_session()
    try:
        resp = session.get(
            "https://gnews.io/api/v4/search",
            params={
                "q":       q_text,
                "lang":    lang,
                "country": country,
                "max":     30,
                "apikey":  api_key,
            },
            timeout=(3.5, 10),
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
            a["image_url"] = a.get("image")
            a["region"] = country.upper()
            a["source_name"] = (a.get("source") or {}).get("name")
            raw_items.append(RawItemDTO(**a))

        log_integration_success(logger, _NAME, items=len(raw_items), query=q_text)
        return raw_items

    except requests.exceptions.RequestException as e:
        if hasattr(e, "response") and e.response is not None and (e.response.status_code == 403 or e.response.status_code == 429):
            log_integration_error(logger, _NAME, e, query=q_text)
            raise PipelineQuotaExceededError("GNews quota exhausted")
        from app.integrations.exceptions import PipelineTransientError
        log_integration_error(logger, _NAME, e, query=q_text)
        raise PipelineTransientError(f"GNews network error: {str(e)}") from e
    except Exception as e:
        from app.integrations.exceptions import PipelineFatalError
        log_integration_error(logger, _NAME, e, query=q_text)
        raise PipelineFatalError(f"GNews unexpected error: {str(e)}") from e
