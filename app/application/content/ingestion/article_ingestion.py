from app.domains.content.models import Article
from .base import generic_ingest
from app.shared.dto.ingestion import EnrichedItemDTO


def create_article_model(data):
    return Article(
        title=data.get("title"),
        description=data.get("description"),
        content_text=data.get("content_text"),
        content_html=data.get("content_html"),
        word_count=data.get("word_count"),
        quality_score=data.get("quality_score", 0.0),
        is_content_scraped=data.get("is_content_scraped", False),
        ingestion_method=data.get("ingestion_method"),
        status=data.get("status", "pending"),
        image_url=data.get("image_url"),
        authors=[data.get("author")] if data.get("author") else None,
        extended_metadata=data.get("extended_metadata"),
        images=data.get("images"),
    )


def ingest_article(session, raw_data):
    # Backward compatibility: wrap dict into EnrichedItemDTO if necessary
    if isinstance(raw_data, dict):
        enriched_dto = EnrichedItemDTO(**raw_data)
    else:
        enriched_dto = raw_data

    # 1. Map to domain DTO via consolidated normalization service
    from app.domains.content.service.normalization import normalize_article_data

    cleaned_dto = normalize_article_data(enriched_dto)
    if not cleaned_dto:
        return None, "skipped"

    # Fallback to dict for generic_ingest compatibility
    cleaned_dict = cleaned_dto.model_dump()

    # Automatically mark newsapi_ai articles as published and scraped
    if cleaned_dict.get("ingestion_method") == "newsapi_ai" or raw_data.get("ingestion_method") == "newsapi_ai":
        cleaned_dict["is_published"] = True
        cleaned_dict["is_content_scraped"] = True
        cleaned_dict["status"] = "complete"

    return generic_ingest(
        session,
        object_type="article",
        raw_data=cleaned_dict,
        model_class=Article,
        factory_func=create_article_model,
    )
