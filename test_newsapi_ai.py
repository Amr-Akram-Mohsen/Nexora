import json
import os
from app.core import create_app
from app.integrations.content.core.api_fetchers import safe_post_json, _parse_to_er_query

app = create_app()

with app.app_context():
    api_key = app.config.get("NEWSAPI_AI_API_KEY")
    query_obj = {"$query": _parse_to_er_query("apple")}
    
    payload = {
        "action": "getArticles",
        "query": query_obj,
        "articlesPage": 1,
        "articlesCount": 1,
        "articlesSortBy": "date",
        "articlesSortByAsc": False,
        "resultType": "articles",
        "apiKey": api_key,
        "includeArticleConcepts": True,
        "includeArticleCategories": True,
    }
    
    import requests
    response = requests.post("https://eventregistry.org/api/v1/article/getArticles", json=payload, timeout=10)
    data = response.json()
    
    articles = data.get("articles", {}).get("results", [])
    if articles:
        article = articles[0]
        print("KEYS IN RESPONSE:", list(article.keys()))
        print("CONCEPTS INCLUDED:", "concepts" in article)
        print("CATEGORIES INCLUDED:", "categories" in article)
        print("EVENTS INCLUDED:", "eventUri" in article)
        
        with open("newsapi_ai_sample.json", "w") as f:
            json.dump(article, f, indent=2)
    else:
        print("No articles returned.")
