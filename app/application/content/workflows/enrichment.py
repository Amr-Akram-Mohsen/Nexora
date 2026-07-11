# app/application/content/workflows/enrichment.py
import logging
from app.core.extensions import db
from app.domains.content.models import Article, Content
from app.shared.utils.logging import (
    log_integration_start,
    log_integration_success,
    log_integration_error,
    log_item_ingested,
    log_item_skipped,
)

logger = logging.getLogger(__name__)

_NAME = "rescrape"


def reprocess_unscraped_articles(limit: int = 50, extractor_service: str = "diffbot") -> int:
    """
    Phase 2: Enrichment Workflow
    Fetches articles in 'pending' / 'failed' status and performs full scraping.
    """
    from datetime import datetime, timedelta
    from app.domains.content.service.query.filtering import get_unscraped_articles, get_content_by_object

    retry_threshold = datetime.utcnow() - timedelta(hours=24)
    unscraped = get_unscraped_articles(limit, retry_threshold)

    if not unscraped:
        log_integration_success(logger, _NAME, items=0, total=0, mode="full_scrape")
        return 0

    log_integration_start(logger, _NAME, mode="full_scrape", processing=len(unscraped), extractor=extractor_service)
    success_count = 0

    from app.integrations.content.enrichment.pipeline import full_article_scraping_pipeline

    for article in unscraped:
        url = article.url or ""
        article.last_enrichment_attempt = datetime.utcnow()

        try:
            raw_data = {
                "url":          url,
                "title":        article.title,
                "description":  article.description,
                "content":      article.content_html,
                "image_url":    article.image_url,
                "canonical_url": article.canonical_url,
            }

            enriched_dto = full_article_scraping_pipeline(raw_data, extractor_service=extractor_service)
            enriched = (
                enriched_dto.model_dump()
                if hasattr(enriched_dto, "model_dump")
                else dict(enriched_dto)
            )

            # Update content ONLY if scraper found something substantial
            new_text = enriched.get("content_text")
            if new_text and len(new_text) > (article.word_count or 0):
                article.content_text     = new_text
                article.content_html     = enriched.get("content_html")
                article.word_count       = enriched.get("word_count", 0)
                article.quality_score    = enriched.get("quality_score", 0.0)
                article.is_content_scraped = enriched.get("is_content_scraped", False)
                article.ingestion_method = enriched.get("ingestion_method")
                article.summary          = enriched.get("summary")
                
                # Extended metadata (tags, categories, etc.)
                article.authors          = enriched.get("authors") or article.authors
                article.extended_metadata = enriched.get("extended_metadata", {})
                article.images            = enriched.get("images")
                article.videos            = enriched.get("videos")
                

            # Backfill missing metadata (conservative — only fill gaps)
            if enriched.get("image_url") and not article.image_url:
                article.image_url = enriched["image_url"]
            if enriched.get("canonical_url") and not article.canonical_url:
                article.canonical_url = enriched["canonical_url"]

            # Quality gate: enough content AND has an image
            is_good_quality = (article.word_count or 0) > 250 and article.image_url

            if is_good_quality:
                article.status = "complete"
                success_count += 1
                log_item_ingested(
                    logger, _NAME, article.title[:60],
                    status="published",
                    words=article.word_count,
                )
            else:
                article.status = "partial" if (article.word_count or 0) > 100 else "failed"
                log_item_skipped(
                    logger, _NAME, article.title[:60],
                    reason=f"quality_gate_{article.status}",
                    words=article.word_count,
                )

            # Sync with Content record
            content_rec = get_content_by_object("article", article.id)
            if content_rec:
                content_rec.is_published = article.status == "complete"
                
                # Automatically apply Diffbot taxonomy relations to the database!
                if article.extended_metadata:
                    from app.domains.content.service.command import apply_relationships
                    from app.domains.content.service.search import populate_content_search_fields
                    
                    raw_data_for_relations = {
                        "extended_metadata": article.extended_metadata,
                        "url": article.url,
                    }
                    apply_relationships(content_rec, raw_data_for_relations, session=db.session)
                    populate_content_search_fields(content_rec, article, "article")

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            article.status = "failed"
            db.session.commit()
            log_item_skipped(logger, _NAME, url[:60], reason="exception", error=str(e))
            log_integration_error(logger, _NAME, e, url=url[:60])

    log_integration_success(
        logger, _NAME,
        items=success_count,
        total=len(unscraped),
    )
    return success_count
