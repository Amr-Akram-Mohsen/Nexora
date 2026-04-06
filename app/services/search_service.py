# app/services/search_service.py
from .article_service import get_search_articles
from .item_service import get_search_items

def unified_search(query: str, limit: int = 50):
    articles = get_search_articles(query)
    items = get_search_items(query)
    return {"articles": articles, "items": items, "total": len(articles) + len(items)}
