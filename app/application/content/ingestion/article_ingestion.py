from app.domains.content.models import Article
from .base import generic_ingest
from app.shared.dto.ingestion import EnrichedItemDTO

def calculate_enrichment_priority(data: dict) -> float:
    """
    Calculates priority for Diffbot enrichment using only pre-enrichment signals.
    Excludes Diffbot-dependent fields (content_text, html, summaries, etc.)
    """
    priority = 0.0
    
    quality_score = data.get("quality_score") or 0.0
    priority += quality_score * 2.0
    
    er_source = data.get("er_source")
    if isinstance(er_source, dict):
        importance = er_source.get("importance", 0.0)
        try:
            priority += float(importance)
        except (ValueError, TypeError):
            pass
            
    er_concepts = data.get("er_concepts")
    if isinstance(er_concepts, list):
        priority += min(1.0, len(er_concepts) * 0.1)
        
    er_categories = data.get("er_categories")
    if isinstance(er_categories, list):
        priority += min(1.0, len(er_categories) * 0.2)
        
    er_location = data.get("er_location")
    if isinstance(er_location, dict) and er_location:
        priority += 0.2
        
    if data.get("er_event_uri") or data.get("er_event_data"):
        priority += 1.5
        
    published_at = data.get("published_at")
    if published_at:
        import datetime
        try:
            if isinstance(published_at, str):
                # basic ISO format parsing
                if published_at.endswith('Z'):
                    published_at = published_at[:-1] + '+00:00'
                pub_date = datetime.datetime.fromisoformat(published_at)
            else:
                pub_date = published_at
                
            if isinstance(pub_date, datetime.datetime):
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=datetime.timezone.utc)
                now = datetime.datetime.now(datetime.timezone.utc)
                age_hours = (now - pub_date).total_seconds() / 3600.0
                if age_hours >= 0:
                    freshness_boost = max(0.0, 1.0 - (age_hours / 48.0))
                    priority += freshness_boost
        except Exception:
            pass
            
    return float(priority)


def create_article_model(data):
    from app.core.extensions import db
    from app.domains.content.models.author import Author
    
    author_objs = []
    authors_data = data.get("authors") or ([data.get("author")] if data.get("author") else [])
    
    for author_data in authors_data:
        if isinstance(author_data, str):
            author_data = {"name": author_data}
            
        name = author_data.get("name")
        if not name:
            continue
            
        # Filter out junk author names like "See full bio"
        if name.strip().lower() in ("see full bio", "full bio", "author", "by"):
            continue
            
        uri = author_data.get("uri")
        url = author_data.get("link") or author_data.get("authorUrl") or author_data.get("url")
        type_val = author_data.get("type", "author")
        is_agency = author_data.get("isAgency", False)
        
        author_obj = Author.get_or_create(
            session=db.session,
            name=name,
            uri=uri,
            url=url,
            type_val=type_val,
            is_agency=is_agency
        )
        if author_obj and author_obj not in author_objs:
            author_objs.append(author_obj)

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
        authors=author_objs,
        language=data.get("language"),
        sentiment_score=data.get("sentiment_score"),
        extended_metadata=data.get("extended_metadata"),
        images=data.get("images"),
        videos=data.get("videos"),
        summary=data.get("summary"),
        enrichment_priority=calculate_enrichment_priority(data),
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
    
    if not article.language:
        article.language = obj.get("humanLanguage")
    if not article.word_count:
        article.word_count = len(article.content_text.split()) if article.content_text else 0
    
    if article.sentiment_score is None:
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
    from app.domains.content.models.author import Author
    
    diffbot_authors_data = []
    if obj.get("authors"):
        diffbot_authors_data = obj.get("authors")
    elif obj.get("author"):
        author_val = obj.get("author")
        if isinstance(author_val, str):
            diffbot_authors_data = [{"name": author_val}]
        elif isinstance(author_val, dict):
            diffbot_authors_data = [author_val]
            
    if diffbot_authors_data:
        existing_authors = article.authors or [] # Now a list of Author objects
        
        for new_a in diffbot_authors_data:
            new_name = new_a.get("name", "") if isinstance(new_a, dict) else str(new_a)
            if not new_name:
                continue
                
            url = None
            if isinstance(new_a, dict):
                url = new_a.get("link") or new_a.get("authorUrl")
                
            # Use get_or_create which handles the alias resolution natively
            author_obj = Author.get_or_create(
                session=session,
                name=new_name,
                url=url
            )
            
            if author_obj and author_obj not in existing_authors:
                existing_authors.append(author_obj)
                
        article.authors = existing_authors

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
                    provider="diffbot"
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


def update_article_model(obj, data):
    changed = False
    if data.get("body") and not obj.body:
        obj.body = data.get("body")
        changed = True
    if data.get("word_count") and not obj.word_count:
        obj.word_count = data.get("word_count")
        changed = True
        
    if data.get("authors") and not obj.authors:
        from app.core.extensions import db
        from app.domains.content.models.author import Author
        author_objs = []
        for author_data in data.get("authors"):
            if isinstance(author_data, str):
                author_data = {"name": author_data}
            name = author_data.get("name")
            if not name: continue
            author_obj = Author.get_or_create(
                session=db.session,
                name=name,
                uri=author_data.get("uri"),
                url=author_data.get("link") or author_data.get("authorUrl") or author_data.get("url"),
                type_val=author_data.get("type", "author"),
                is_agency=author_data.get("isAgency", False)
            )
            if author_obj and author_obj not in author_objs:
                author_objs.append(author_obj)
        if author_objs:
            obj.authors = author_objs
            changed = True
            
    if data.get("language") and not obj.language:
        obj.language = data.get("language")
        changed = True
    if data.get("sentiment_score") is not None and obj.sentiment_score is None:
        obj.sentiment_score = data.get("sentiment_score")
        changed = True
    return changed

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
        update_func=update_article_model,
    )
