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


def enrich_discovered_articles(limit: int = 50) -> int:
    """
    Phase 2: Enrichment Workflow
    Fetches articles in 'discovered' / 'failed' status and performs Diffbot enrichment.
    """
    from datetime import datetime, timedelta
    from app.domains.content.service.query.filtering import get_unscraped_articles, get_content_by_object
    from app.application.content.ingestion.article_ingestion import process_diffbot_enrichment
    from app.integrations.content.utilities.extractor_clients import diffbot_extract

    retry_threshold = datetime.utcnow() - timedelta(hours=24)
    unscraped = get_unscraped_articles(limit, retry_threshold)

    if not unscraped:
        log_integration_success(logger, _NAME, products=0, total=0, mode="diffbot_enrich")
        return 0

    log_integration_start(logger, _NAME, mode="diffbot_enrich", processing=len(unscraped), extractor="diffbot")
    success_count = 0

    for article in unscraped:
        url = article.url or article.canonical_url
        if not url:
            article.status = "failed"
            db.session.commit()
            continue
            
        article.last_enrichment_attempt = datetime.utcnow()

        try:
            # Call Diffbot directly
            diffbot_data = diffbot_extract(url)
            
            is_success = process_diffbot_enrichment(article, diffbot_data, db.session)

            if is_success:
                # Quality gate
                is_good_quality = (article.word_count or 0) > 250 and article.image_url
                
                content_rec = get_content_by_object("article", article.id)
                
                if is_good_quality:
                    # Auto-publish policy: if it passes the quality gate, publish it immediately
                    article.status = "published"
                    success_count += 1
                    
                    if content_rec:
                        content_rec.is_published = True
                        log_item_ingested(
                            logger, _NAME,
                            content_id=content_rec.id,
                            object_id=article.id,
                            status="published",
                            words=article.word_count,
                        )
                else:
                    article.status = "failed"
                    log_item_skipped(
                        logger, _NAME, article.title[:60],
                        reason=f"quality_gate_{article.status}",
                        words=article.word_count,
                    )

                if content_rec:
                    from app.domains.content.service.search import populate_content_search_fields
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
        products=success_count,
        total=len(unscraped),
    )
    return success_count
