# app/application/content/workflows/enrichment.py
import logging
from app.core.extensions import db
from app.domains.content.models import Article, Content
from app.shared.utils.logging import log_scrape_start, log_scrape_success, log_scrape_error

logger = logging.getLogger(__name__)

_NAME = "rescrape"


def reprocess_unscraped_articles(limit: int = 50) -> int:
    """
    Finds articles stored in 'pending' status and attempts to fully enrich them.
    Targets articles waiting for scraping or with poor initial metadata.
    """
    unscraped = (
        db.session.query(Article)
        .join(Content, (Content.object_type == "article") & (Content.object_id == Article.id) & (Content.is_active == True))
        .filter(Article.status == "pending")
        .order_by(Content.published_at.desc())
        .limit(limit)
        .all()
    )

    if not unscraped:
        logger.info("[%s] no articles in 'pending' status needing enrichment", _NAME)
        return 0

    logger.info("[%s] start  processing=%d articles", _NAME, len(unscraped))
    success_count = 0

    from app.integrations.enrichment.pipeline import enrich_article_content
    from datetime import datetime

    for article in unscraped:
        url = article.url or ""
        log_scrape_start(logger, url)
        
        try:
            raw_data = {
                "url":         url,
                "title":       article.title,
                "description": article.description,
                "content":     article.content_html,
                "image_url":   article.image_url,
                "canonical_url": article.canonical_url,
            }

            # Run full enrichment (scraping enabled)
            enriched_dto = enrich_article_content(raw_data, should_scrape=True)
            
            # Convert DTO to dict for easy access
            if hasattr(enriched_dto, "model_dump"):
                enriched = enriched_dto.model_dump()
            else:
                enriched = dict(enriched_dto)

            article.last_enrichment_attempt = datetime.utcnow()

            # Update core fields
            article.content_text       = enriched.get("content_text")
            article.content_html       = enriched.get("content_html")
            article.word_count         = enriched.get("word_count", 0)
            article.quality_score      = enriched.get("quality_score", 0.0)
            article.is_content_scraped  = enriched.get("is_content_scraped", False)
            article.content_source     = enriched.get("content_source")
            
            # Backfill missing image/canonical if recovered
            if enriched.get("image_url"):
                article.image_url = enriched["image_url"]
            if enriched.get("canonical_url"):
                article.canonical_url = enriched["canonical_url"]

            # --- Quality Gate ---
            # Threshold: > 250 words AND has an image
            is_good_quality = article.word_count > 250 and article.image_url
            
            if is_good_quality:
                article.status = "complete"
                # Update the associated Content record
                content_rec = Content.query.filter_by(object_type="article", object_id=article.id).first()
                if content_rec:
                    content_rec.is_published = True
                success_count += 1
                log_scrape_success(logger, url, words=article.word_count, source=article.content_source)
            else:
                # Still failing quality gate - mark as partial or failed
                article.status = "failed" if article.word_count < 100 else "partial"
                content_rec = Content.query.filter_by(object_type="article", object_id=article.id).first()
                if content_rec:
                    content_rec.is_published = False
                log_scrape_error(logger, url, reason=f"low_quality (words={article.word_count}, img={bool(article.image_url)})")

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            article.status = "failed"
            db.session.commit()
            log_scrape_error(logger, url, reason=f"exception: {str(e)}")

    logger.info("[%s] done  published=%d / %d", _NAME, success_count, len(unscraped))
    return success_count
