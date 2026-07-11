import sys
import logging
import json
import requests
from app.core import create_app
from app.integrations.content.core.api_fetchers import _parse_to_er_query, fetch_newsapi_ai_query

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

app = create_app()
with app.app_context():
    q_text = "(Tablets OR iPad OR android tablet OR drawing OR e-reader) (news OR launch OR release)"
    q_obj = {
        "query": q_text,
        "from": "2024-06-09",
        "to": "2024-07-09"
    }
    
    print("\nExecuting fetch with 2024 dates (YYYY-MM-DD)...")
    res = fetch_newsapi_ai_query(q_obj)
    print(f"Results fetched: {len(res) if res else 0}")

    q_obj_full = {
        "query": q_text,
        "from": "2024-06-09T04:51:08Z",
        "to": "2024-07-09T04:51:08Z"
    }
    
    print("\nExecuting fetch with 2024 dates (ISO Z)...")
    res_full = fetch_newsapi_ai_query(q_obj_full)
    print(f"Results fetched: {len(res_full) if res_full else 0}")
