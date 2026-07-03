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


def _parse_blocks_from_markdown(article: Article) -> bool:
    """
    Re-parse content_blocks from an already-scraped article's content_markdown
    WITHOUT making any network calls. Used for articles that have markdown but
    no blocks yet.

    Returns True if blocks were successfully parsed and saved.
    """
    from app.application.content.ingestion.normalizer import normalize_markdown

    # Pass the article's own URL so same-domain link filtering applies
    result = normalize_markdown(
        article.content_markdown,
        source_url=article.url,
        hero_image_url=article.image_url,
    )
    blocks = result.get("content_blocks")
    stats  = result.get("stats", {})

    if blocks:
        article.content_blocks = blocks
        logger.debug(
            "[reparse] article_id=%s  blocks=%d  paragraphs=%d  words=%d",
            article.id,
            stats.get("output_blocks", len(blocks)),
            stats.get("paragraphs", 0),
            stats.get("total_words", 0),
        )
        return True

    logger.debug(
        "[reparse] article_id=%s  gate=FAIL  words=%d",
        article.id,
        stats.get("total_words", 0),
    )
    return False


def reprocess_unscraped_articles(limit: int = 50, extractor_service: str = "firecrawl") -> int:
    """
    Phase 2: Enrichment Workflow

    Priority order:
      1. Articles that are already scraped (have content_markdown) but have no
         content_blocks yet — re-parse locally, no network call needed.
      2. Articles in 'pending' / 'failed' status — perform full scraping.

    Both groups are processed within the *limit* budget.
    """
    from datetime import datetime, timedelta

    retry_threshold = datetime.utcnow() - timedelta(hours=24)

    from app.domains.content.service.query.filtering import (
        get_unscraped_articles,
        get_markdown_only_articles,
        get_content_by_object,
    )

    # ── PASS 1: local re-parse for markdown-only articles ─────────────────
    markdown_only = get_markdown_only_articles(limit)
    reparse_count = 0

    if markdown_only:
        log_integration_start(logger, _NAME, mode="reparse_blocks", processing=len(markdown_only))
        for article in markdown_only:
            try:
                success = _parse_blocks_from_markdown(article)
                if success:
                    reparse_count += 1
                    log_item_ingested(
                        logger, _NAME, article.title[:60],
                        status="blocks_parsed",
                        words=article.word_count,
                    )
                else:
                    log_item_skipped(
                        logger, _NAME, article.title[:60],
                        reason="blocks_validation_failed",
                    )
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                log_item_skipped(logger, _NAME, str(article.id), reason="reparse_exception", error=str(e))

    # Remaining budget for full scraping
    remaining = max(0, limit - len(markdown_only))
    if remaining == 0:
        log_integration_success(logger, _NAME, items=reparse_count, total=len(markdown_only), mode="reparse_only")
        return reparse_count

    # ── PASS 2: full scraping for unscraped articles ───────────────────────
    unscraped = get_unscraped_articles(remaining, retry_threshold)

    if not unscraped:
        log_integration_success(logger, _NAME, items=reparse_count, total=len(markdown_only), mode="reparse_only")
        return reparse_count

    log_integration_start(logger, _NAME, mode="full_scrape", processing=len(unscraped), extractor=extractor_service)
    success_count = reparse_count

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
                article.content_markdown = enriched.get("content_markdown")
                article.content_blocks   = enriched.get("content_blocks")
                article.word_count       = enriched.get("word_count", 0)
                article.quality_score    = enriched.get("quality_score", 0.0)
                article.is_content_scraped = enriched.get("is_content_scraped", False)
                article.content_source   = enriched.get("content_source")
                article.author           = enriched.get("author") or article.author
                article.extended_metadata = enriched.get("extended_metadata")
                article.extracted_images  = enriched.get("extracted_images")

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
        total=len(markdown_only) + len(unscraped),
        reparsed=reparse_count,
    )
    return success_count
