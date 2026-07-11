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
        ingestion_method=data.get("ingestion_method"),
        status=data.get("status", "discovered"),
        image_url=data.get("image_url"),
        authors=data.get("authors") or ([data.get("author")] if data.get("author") else None),
        extended_metadata=data.get("extended_metadata"),
        images=data.get("images"),
        videos=data.get("videos"),
        summary=data.get("summary"),
    )

def process_diffbot_enrichment(article, diffbot_data, session):
    """
    Applies Diffbot enrichment data to a discovered Article.
    Updates content fields, extracts authors, and manages the status transition.
    """
    if not diffbot_data or "objects" not in diffbot_data or not diffbot_data["objects"]:
        article.status = "failed"
        return False

    obj = diffbot_data["objects"][0]
    
    # 1. Update Core Content Fields
    article.content_text = obj.get("text")
    article.content_html = obj.get("html")
    article.summary = obj.get("summary")
    article.language = obj.get("humanLanguage")
    article.word_count = len(article.content_text.split()) if article.content_text else 0
    article.sentiment_score = obj.get("sentiment")
    
    # 2. Extract Media
    if "images" in obj:
        article.images = [{"url": img.get("url"), "title": img.get("title")} for img in obj.get("images", [])]
    if "videos" in obj:
        article.videos = [{"url": vid.get("url")} for vid in obj.get("videos", [])]

    # 3. Handle Authors
    authors = []
    if "author" in obj:
        authors.append(obj["author"])
    if "authors" in obj:
        authors.extend([a.get("name") for a in obj["authors"] if a.get("name")])
    if authors:
        article.authors = list(set(authors))

    # 4. Integrate Diffbot Tags (via ContentEntity)
    if "tags" in obj:
        from app.domains.relationships import ContentEntity
        from app.domains.taxonomy.models import Entity
        
        # Get the wrapper Content object
        from app.domains.content.models.content import Content
        content = session.query(Content).filter_by(object_type="article", object_id=article.id).first()
        
        if content:
            for tag in obj.get("tags", []):
                label = tag.get("label")
                uri = tag.get("uri")
                score = tag.get("score", 0.0)
                
                if not label:
                    continue
                
                entity = Entity.get_or_create(
                    name=label,
                    session=session,
                    external_uri=uri,
                    entity_type="tag",
                    provider="diffbot",
                    provider_confidence=score
                )
                
                if entity:
                    ContentEntity.get_or_create(
                        content_id=content.id,
                        entity_id=entity.id,
                        session=session,
                        origin="diffbot",
                        relevance_score=score * 100 if score <= 1 else score,
                        confidence=score if score <= 1 else score / 100.0
                    )

    # 5. Transition Status
    article.status = "enriching"
    return True


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
        factory_func=create_article_model,
    )
