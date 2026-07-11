import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

from app.core import create_app
from app.integrations.content.core.api_fetchers import fetch_newsapi_ai_query

app = create_app()
with app.app_context():
    try:
        print("Starting fetch...")
        res = fetch_newsapi_ai_query({"query": "apple"})
        print("RESULT:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("ERROR:", e)
