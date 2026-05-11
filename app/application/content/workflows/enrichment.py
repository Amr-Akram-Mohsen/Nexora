# app/application/content/workflows/enrichment.py
import logging
from app.core.extensions import db
from app.domains.content.models import Article, Content
from app.shared.utils.logging import log_scrape_start, log_scrape_success, log_scrape_error

logger = logging.getLogger(__name__)

_NAME = "rescrape"


def reprocess_unscraped_articles(limit: int = 50) -> int:
    """
    Phase 2: Enrichment Workflow
    Finds articles in 'pending' status and performs full-body scraping.
    """
    from datetime import datetime, timedelta
    
    # Only retry 'failed' articles after 24 hours
    retry_threshold = datetime.utcnow() - timedelta(hours=24)
    
    unscraped = (
        db.session.query(Article)
        .join(Content, (Content.object_type == "article") & (Content.object_id == Article.id))
        .filter(
            (Article.status == "pending") | 
            ((Article.status == "failed") & (Article.last_enrichment_attempt < retry_threshold))
        )
        .order_by(Content.published_at.desc())
        .limit(limit)
        .all()
    )

    if not unscraped:
        logger.info("[%s] no articles needing enrichment at this time", _NAME)
        return 0

    logger.info("[%s] phase_2_start  processing=%d articles", _NAME, len(unscraped))
    success_count = 0

    from app.integrations.enrichment.pipeline import full_article_scraping_pipeline

    for article in unscraped:
        url = article.url or ""
        article.last_enrichment_attempt = datetime.utcnow()
        
        try:
            # Prepare data for pipeline
            raw_data = {
                "url":           url,
                "title":         article.title,
                "description":   article.description,
                "content":       article.content_html,
                "image_url":     article.image_url,
                "canonical_url": article.canonical_url,
            }

            # Run Phase 2 Enrichment (Heavy Scraping)
            enriched_dto = full_article_scraping_pipeline(raw_data)
            enriched = enriched_dto.model_dump() if hasattr(enriched_dto, "model_dump") else dict(enriched_dto)

            # Update content ONLY if scraper found something substantial
            new_text = enriched.get("content_text")
            if new_text and len(new_text) > (article.word_count or 0):
                article.content_text       = new_text
                article.content_html       = enriched.get("content_html")
                article.word_count         = enriched.get("word_count", 0)
                article.quality_score      = enriched.get("quality_score", 0.0)
                article.is_content_scraped  = enriched.get("is_content_scraped", False)
                article.content_source     = enriched.get("content_source")
            
            # Backfill missing metadata (conservative approach)
            if enriched.get("image_url") and not article.image_url:
                article.image_url = enriched["image_url"]
            if enriched.get("canonical_url") and not article.canonical_url:
                article.canonical_url = enriched["canonical_url"]

            # --- Quality Gate ---
            # Threshold: Sufficient content length AND has a valid image
            is_good_quality = (article.word_count or 0) > 250 and article.image_url
            
            if is_good_quality:
                article.status = "complete"
                success_count += 1
            else:
                article.status = "partial" if (article.word_count or 0) > 100 else "failed"

            # Sync with Content record
            content_rec = Content.query.filter_by(object_type="article", object_id=article.id).first()
            if content_rec:
                content_rec.is_published = (article.status == "complete")

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            article.status = "failed"
            db.session.commit()
            logger.error("[%s] error  url=%s  err=%s", _NAME, url[:60], str(e))

    logger.info("[%s] phase_2_done  success=%d / %d", _NAME, success_count, len(unscraped))
    return success_count
