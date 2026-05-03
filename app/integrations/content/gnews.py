# app/integrations/content/gnews.py
import logging
import requests
from flask import current_app
from app.integrations.exceptions import PipelineQuotaExceededError

logger = logging.getLogger(__name__)

def fetch_gnews_query(q_obj: dict, **kwargs) -> list[dict]:
    """
    Pure fetcher for GNews.
    """
    api_key = current_app.config.get("GNEWS_API_KEY")
    if not api_key:
        logger.warning("[GNews] No API key")
        print("[GNews] No API key")
        return []

    q_text = q_obj["query"]
    country = q_obj.get("region", "sa").lower()
    
    try:
        resp = requests.get(
            "https://gnews.io/api/v4/search",
            params={
                "q":       q_text,
                "lang":    "en" if not any(c in q_text for c in 'ءآأؤإئبةتثجحخدذرزسشصضطظعغفقكلمنهوي') else "ar",
                "country": country,
                "max":     50,
                "apikey":  api_key,
            },
            timeout=10,
        )
        resp.raise_for_status()
        
        from app.shared.dto.ingestion import RawItemDTO
        articles = resp.json().get("articles", [])
        raw_items = []
        for a in articles:
            a["image_url"] = a.get("image")
            a["region"] = country.upper()
            raw_items.append(RawItemDTO(**a))
        return raw_items
        
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 403:
            raise PipelineQuotaExceededError("GNews Quota Exceeded")
        logger.warning("[GNews] API request failed for query '%s': %s", q_text, str(e))
        return []
