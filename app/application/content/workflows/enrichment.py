# app/domains/article/service/scraping.py
import logging
from app.core.extensions import db
from app.domains.content.models import Article

logger = logging.getLogger(__name__)

def reprocess_unscraped_articles(limit: int = 50):
    """
    Finds articles that were stored without full content and attempts to re-scrape them.
    Now looks for articles with low word count or missing content_text.
    """
    from sqlalchemy import or_
    unscraped = (
        Article.query.filter(
            Article.is_active == True,
            or_(
                Article.word_count == None,
                Article.word_count < 300,
                Article.quality_score < 0.5,
                Article.content_text == None
            )
        )
        .order_by(Article.published_at.desc())
        .limit(limit)
        .all()
    )

    if not unscraped:
        logger.info("[ScrapingService] No articles needing enrichment found.")
        return 0

    logger.info(f"[ScrapingService] Found {len(unscraped)} articles to enrich.")
    success_count = 0

    from app.integrations.enrichment.pipeline import enrich_article_content

    for article in unscraped:
        try:
            # 1. Prepare raw data for enrichment
            raw_data = {
                "url": article.url,
                "title": article.title,
                "description": article.description,
                "content": article.content_html or article.body,
            }

            # 2. Run enrichment (this will trigger scraping if trusted)
            enriched = enrich_article_content(raw_data)
            
            # 3. Check if we got more content or better quality
            current_quality = getattr(article, 'quality_score', 0.0) or 0.0
            new_quality = enriched.get("quality_score", 0.0)
            
            if enriched.get("word_count", 0) > (article.word_count or 0) or new_quality > current_quality:
                article.content_text = enriched["content_text"]
                article.content_html = enriched["content_html"]
                article.word_count = enriched["word_count"]
                article.quality_score = new_quality
                article.is_content_scraped = enriched.get("is_content_scraped", False)
                article.content_source = enriched.get("content_source")
                
                db.session.commit()
                success_count += 1
                logger.info(f"[ScrapingService] Successfully enriched: {article.title[:50]}")
            
        except Exception:
            db.session.rollback()
            logger.exception(f"[ScrapingService] Error enriching article ID {article.id}")

    return success_count
