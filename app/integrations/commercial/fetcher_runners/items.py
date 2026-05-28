import logging
from flask import current_app
from app.integrations.ecommerce.amazon import search_products
from app.application.item.workflows.ingestion import store_amazon_item
from app.integrations.external.api import mark_fetched, _record_call

logger = logging.getLogger(__name__)

def run_item_fetch():
    """Fetches items for discovery from Amazon PA-API."""
    queries = [
        {"q": "smartphones 2025", "cat": "smartphones"},
        {"q": "gaming laptops", "cat": "laptops"}
    ]
    
    if not current_app.config.get("AMAZON_ACCESS_KEY"):
        logger.warning("[ItemFetch] Amazon credentials missing.")
        return 0
        
    stored = 0
    for q in queries:
        try:
            results = search_products(q["q"], marketplace="sa", category_query=q["cat"], max_results=5)
            _record_call("amazon_sa")
            mark_fetched(section="tech", query_text=q["q"], category=q["cat"], source="amazon_sa", normalized_query=q["q"])
            for r in results:
                item = store_amazon_item(r)
                if item:
                    stored += 1
        except Exception as e:
            logger.exception(f"[ItemFetch] Error fetching {q['q']}")
            
    return stored
