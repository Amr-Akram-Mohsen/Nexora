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


def enrich_discovered_articles(limit: int = 50, force: bool = False) -> dict:
    """
    Phase 2: Enrichment Workflow
    Fetches articles in 'discovered' / 'failed' status and performs Diffbot enrichment.
    """
    from datetime import datetime, timedelta
    from app.domains.content.service.query.filtering import get_unscraped_articles, get_content_by_object
    from app.application.content.ingestion.article_ingestion import process_diffbot_enrichment
    from app.application.content.ingestion.scraper_pipeline import fetch_and_clean_diffbot

    retry_threshold = datetime.utcnow() + timedelta(days=365) if force else datetime.utcnow() - timedelta(hours=24)
    unscraped = get_unscraped_articles(limit, retry_threshold)

    if not unscraped:
        log_integration_success(logger, _NAME, products=0, total=0, mode="diffbot_enrich")
        return {"processed": 0, "published": 0, "failed_network": 0, "failed_quality_length": 0, "failed_quality_media": 0, "failed_other": 0, "details": []}

    log_integration_start(logger, _NAME, mode="diffbot_enrich", processing=len(unscraped), extractor="diffbot")
    
    results = {
        "processed": len(unscraped),
        "published": 0,
        "failed_network": 0,
        "failed_quality_length": 0,
        "failed_quality_media": 0,
        "failed_other": 0,
        "details": []
    }

    for article in unscraped:
        url = article.url or article.canonical_url
        if not url:
            article.status = "failed"
            db.session.commit()
            continue
            
        article.last_enrichment_attempt = datetime.utcnow()

        try:
            # Call Diffbot directly
            diffbot_data = fetch_and_clean_diffbot(url)
            
            is_success = process_diffbot_enrichment(article, diffbot_data, db.session)

            if is_success:
                # Quality gate
                has_length = (article.word_count or 0) > 250
                has_media = bool(article.image_url)
                is_good_quality = has_length and has_media
                
                content_rec = get_content_by_object("article", article.id)
                
                if is_good_quality:
                    # Auto-publish policy: if it passes the quality gate, publish it immediately
                    article.status = "published"
                    results["published"] += 1
                    results["details"].append({"title": article.title, "status": "success", "url": url})
                    
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
                    if not has_length:
                        results["failed_quality_length"] += 1
                        results["details"].append({"title": article.title, "status": "failed", "reason": "too_short", "url": url})
                    elif not has_media:
                        results["failed_quality_media"] += 1
                        results["details"].append({"title": article.title, "status": "failed", "reason": "no_media", "url": url})
                    
                    log_item_skipped(
                        logger, _NAME, article.title[:60],
                        reason=f"quality_gate_{article.status}",
                        words=article.word_count,
                    )

                if content_rec:
                    from app.domains.content.service.public.search import populate_content_search_fields
                    from app.domains.content.service.command import recalculate_content_score
                    populate_content_search_fields(content_rec, article, "article")
                    recalculate_content_score(content_rec, article)
            else:
                results["failed_network"] += 1
                results["details"].append({"title": article.title, "status": "failed", "reason": "network_or_extractor_error", "url": url})

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            article.status = "failed"
            db.session.commit()
            results["failed_other"] += 1
            results["details"].append({"title": article.title, "status": "failed", "reason": str(e), "url": url})
            log_item_skipped(logger, _NAME, url[:60], reason="exception", error=str(e))
            log_integration_error(logger, _NAME, e, url=url[:60])

        import time
        time.sleep(1.5)  # Pace requests to avoid 429 Too Many Requests

    log_integration_success(
        logger, _NAME,
        products=results["published"],
        total=len(unscraped),
    )
    return results
