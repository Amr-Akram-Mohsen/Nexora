from app.domains.content.models import Article
from .base import generic_ingest
from app.shared.dto.ingestion import EnrichedItemDTO


def create_article_model(data):
    return Article(
        title=data.get("title"),
        description=data.get("description"),
        body=data.get("body"),
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
    if not diffbot_data or "metadata" not in diffbot_data:
        article.status = "failed"
        return False

    obj = diffbot_data["metadata"]
    
    # 1. Update Core Content Fields
    article.content_text = obj.get("text")
    article.content_html = obj.get("html")
    article.language = obj.get("humanLanguage")
    article.word_count = len(article.content_text.split()) if article.content_text else 0
    article.sentiment_score = obj.get("sentiment")
    
    summary = obj.get("summary")
    if summary:
        import re
        from difflib import SequenceMatcher
        
        def _norm(t):
            return re.sub(r'[^a-z0-9]', '', (t or "").lower())
            
        norm_sum = _norm(summary)
        if len(norm_sum) > 20:
            norm_desc = _norm(article.description)
            norm_text_start = _norm(article.content_text[:len(summary) * 2 + 400]) if article.content_text else ""
            
            is_redundant = False
            
            if norm_sum in norm_text_start or (norm_desc and (norm_sum in norm_desc or norm_desc in norm_sum)):
                is_redundant = True
            elif norm_desc and SequenceMatcher(None, norm_sum, norm_desc).ratio() > 0.85:
                is_redundant = True
            elif norm_text_start:
                prefix = norm_text_start[:len(norm_sum) + 100]
                if len(prefix) > 20:
                    match = SequenceMatcher(None, norm_sum, prefix).find_longest_match(0, len(norm_sum), 0, len(prefix))
                    # If the longest contiguous matching block is at least 80% of the summary length, consider it redundant
                    if match.size > len(norm_sum) * 0.8:
                        is_redundant = True
                    # Also try ratio on the direct slice just in case
                    elif SequenceMatcher(None, norm_sum, norm_text_start[:len(norm_sum)]).ratio() > 0.85:
                        is_redundant = True
                    
            if is_redundant:
                summary = None
            
    article.summary = summary
    # 2. Extract Media
    if "images" in obj:
        article.images = obj.get("images", [])
    if "videos" in obj:
        article.videos = obj.get("videos", [])

    # 3. Handle Authors
    authors = []
    if obj.get("authors"):
        authors = obj.get("authors")
    elif obj.get("author"):
        author_val = obj.get("author")
        if isinstance(author_val, str):
            authors = [{"name": author_val}]
        elif isinstance(author_val, dict):
            authors = [author_val]
            
    if authors:
        article.authors = authors

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
