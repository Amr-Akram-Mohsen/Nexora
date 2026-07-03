from app.domains.content.models import Article
from .base import generic_ingest
from app.shared.dto.ingestion import EnrichedItemDTO


def create_article_model(data):
    return Article(
        title=data.get("title"),
        description=data.get("description"),
        content_text=data.get("content_text"),
        content_html=data.get("content_html"),
        content_markdown=data.get("content_markdown"),
        content_blocks=data.get("content_blocks"),
        word_count=data.get("word_count"),
        quality_score=data.get("quality_score", 0.0),
        is_content_scraped=data.get("is_content_scraped", False),
        content_source=data.get("content_source"),
        status=data.get("status", "pending"),
        body=data.get("content"),  # Still populate body for migration
        image_url=data.get("image_url"),
        author=data.get("author"),
        extended_metadata=data.get("extended_metadata"),
        extracted_images=data.get("extracted_images"),
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

    return generic_ingest(
        session,
        object_type="article",
        raw_data=cleaned_dict,
        model_class=Article,
        factory_func=create_article_model,
    )
