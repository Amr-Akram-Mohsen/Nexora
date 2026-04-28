# app/domains/article/service/scraping.py
import logging
from app.core.extensions import db
from ..models import Article
from app.integrations.cleaner import clean_article_data

logger = logging.getLogger(__name__)

def reprocess_unscraped_articles(limit: int = 50):
    """
    Finds articles that were stored without full content and attempts to re-scrape them.
    """
    unscraped = (
        Article.query.filter_by(is_content_scraped=False, is_active=True)
        .order_by(Article.published_at.desc())
        .limit(limit)
        .all()
    )

    if not unscraped:
        logger.info("[ScrapingService] No unscraped articles found.")
        return 0

    logger.info(f"[ScrapingService] Found {len(unscraped)} articles to re-scrape.")
    success_count = 0

    for article in unscraped:
        try:
            # ── CROSS-SOURCE SCRAPING STRATEGY ──
            # We try every URL linked to this article in the article_sources table
            # until one of them returns high-quality content.
            
            # 1. Get all source URLs (primary + others)
            urls_to_try = [article.url]
            from app.domains.relationships import article_sources
            other_sources = db.session.query(article_sources.c.url).filter_by(article_id=article.id).all()
            for row in other_sources:
                if row.url not in urls_to_try:
                    urls_to_try.append(row.url)

            success = False
            for target_url in urls_to_try:
                logger.info(f"[ScrapingService] Trying source: {target_url}")
                
                # Treat article as raw data
                raw_data = {
                    "url": target_url,
                    "title": article.title,
                    "description": article.description,
                }

                # Run cleaner WITH scraping
                cleaned = clean_article_data(raw_data, skip_scrape=False)
                
                if cleaned and cleaned.get("is_content_scraped"):
                    article.content = cleaned["content"]
                    article.is_content_scraped = True
                    # If the successful URL was different from the primary, update the primary to the working one
                    if target_url != article.url:
                        article.url = target_url
                    
                    db.session.commit()
                    success = True
                    success_count += 1
                    logger.info(f"[ScrapingService] Success! Recovered content via: {target_url}")
                    break # Stop trying other sources for this article
            
            if not success:
                logger.warning(f"[ScrapingService] All {len(urls_to_try)} sources failed for: {article.title[:50]}")
        
        except Exception:
            db.session.rollback()
            logger.exception(f"[ScrapingService] Error re-scraping article ID {article.id}")

    return success_count
