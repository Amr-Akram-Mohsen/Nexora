import os
import json
from main import app
from app.integrations.content.core.api_fetchers import fetch_newsapi_ai_query

with app.app_context():
    data = fetch_newsapi_ai_query({"query": "technology", "category": "tech"})
    if data:
        events = [d for d in data if d.er_event_uri]
        print(f"Total articles: {len(data)}")
        print(f"Articles with eventUri: {len(events)}")
        if events:
            print("First article event data:", events[0].er_event_data)
    else:
        print("No data fetched")
