# app/application/content/workflows/enrichment.py
import logging
from app.core.extensions import db
from app.domains.content.models import Article
from app.shared.utils.logging import log_scrape_start, log_scrape_success, log_scrape_error

logger = logging.getLogger(__name__)

_NAME = "rescrape"


def reprocess_unscraped_articles(limit: int = 50) -> int:
    """
    Finds articles stored without full content and attempts to re-scrape them.
    Targets articles with a low word count, missing content, or poor quality score.

    Returns:
        Number of articles successfully enriched.
    """
    from sqlalchemy import or_
    unscraped = (
        Article.query.filter(
            Article.is_active == True,
            or_(
                Article.word_count == None,
                Article.word_count < 300,
                Article.quality_score < 0.5,
                Article.content_text == None,
            )
        )
        .order_by(Article.published_at.desc())
        .limit(limit)
        .all()
    )

    if not unscraped:
        logger.info("[%s] no articles needing enrichment", _NAME)
        return 0

    logger.info("[%s] start  found=%d articles to enrich", _NAME, len(unscraped))
    success_count = 0

    from app.integrations.enrichment.pipeline import enrich_article_content

    for article in unscraped:
        url = article.url or ""
        title_short = (article.title or "")[:60]

        log_scrape_start(logger, url)
        try:
            raw_data = {
                "url":         url,
                "title":       article.title,
                "description": article.description,
                "content":     article.content_html or article.body,
            }

            # Re-enrichment always enables scraping (this is its purpose)
            enriched = enrich_article_content(raw_data, should_scrape=True)

            current_quality = getattr(article, "quality_score", 0.0) or 0.0
            new_quality = enriched.get("quality_score", 0.0)

            improved = (
                enriched.get("word_count", 0) > (article.word_count or 0)
                or new_quality > current_quality
            )

            if improved:
                article.content_text      = enriched["content_text"]
                article.content_html      = enriched["content_html"]
                article.word_count        = enriched["word_count"]
                article.quality_score     = new_quality
                article.is_content_scraped = enriched.get("is_content_scraped", False)
                article.content_source    = enriched.get("content_source")

                db.session.commit()
                success_count += 1
                log_scrape_success(
                    logger, url,
                    words=enriched["word_count"],
                    source=enriched.get("content_source", "scraper"),
                )
            else:
                log_scrape_error(
                    logger, url,
                    reason=f"no_improvement  title={title_short!r}",
                )

        except Exception:
            db.session.rollback()
            log_scrape_error(logger, url, reason="exception  see ERROR log below")
            logger.exception("[%s] unhandled error for article id=%s", _NAME, article.id)

    logger.info("[%s] done  success=%d / %d", _NAME, success_count, len(unscraped))
    return success_count
