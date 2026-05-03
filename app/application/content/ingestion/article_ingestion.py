from app.domains.content.models import Article
from .base import generic_ingest
from app.integrations.content.article_utils.cleaner import clean_article_data

def create_article_model(data):
    return Article(
        title=data.get("title"),
        description=data.get("description"),
        content_text=data.get("content_text"),
        content_html=data.get("content_html"),
        word_count=data.get("word_count"),
        quality_score=data.get("quality_score", 0.0),
        is_content_scraped=data.get("is_content_scraped", False),
        content_source=data.get("content_source"),
        body=data.get("content"),  # Still populate body for migration
        image_url=data.get("image_url")
    )

def ingest_article(session, raw_data):
    # 1. Clean metadata
    cleaned = clean_article_data(raw_data)
    if not cleaned:
        return None

    return generic_ingest(
        session,
        object_type="article",
        raw_data=cleaned,
        model_class=Article,
        factory_func=create_article_model
    )