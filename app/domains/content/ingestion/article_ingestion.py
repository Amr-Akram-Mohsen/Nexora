from ..models import Article
from .base import generic_ingest
from app.integrations.cleaner import clean_article_data

def create_article_model(data):
    return Article(
        title=data.get("title"),
        description=data.get("description"),
        body=data.get("content"),
        image_url=data.get("image_url")
    )

def ingest_article(session, raw_data):
    cleaned = clean_article_data(raw_data)
    if not cleaned:
        return None

    # For articles, we still use title-based dedup if external_id is missing
    # but generic_ingest handles the rest.
    # Note: I'll stick to external_id if possible, but many RSS feeds don't have it.
    # So we might need a small tweak in base or just handle it here.
    
    return generic_ingest(
        session,
        object_type="article",
        raw_data=cleaned,
        model_class=Article,
        factory_func=create_article_model
    )