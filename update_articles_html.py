import os
import time
import logging
from dotenv import load_dotenv

# Load environment variables (including DATABASE_URL)
load_dotenv()

from app import create_app
from app.models import db, Article
from app.utils.article_extractor import scrape_article_content, enhance_article_html
from app.scrapers.cleaner import _sanitize_content

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def update_existing_articles():
    # Setup flask app context so SQLAlchemy knows about the DB connection
    app = create_app()
    with app.app_context():
        
        # 1. We ONLY want to update articles that don't have proper HTML tags (i.e. broken ones).
        # We also skip youtube links as they do not have text articles to scrape.
        # The '~Article.content.like(r"%<p>%")' ensures we only fetch flat non-HTML content.
        query = Article.query.filter(
            Article.url.notlike("%youtube.com%")
        )
        
        broken_articles = query.all()
        total = len(broken_articles)
        logger.info(f"Found {total} articles that need HTML rewriting.")

        if total == 0:
            logger.info("Nothing to do! All articles are either perfect or already processed.")
            return

        success_count = 0
        
        for idx, article in enumerate(broken_articles, 1):
            url = article.url
            logger.info(f"[{idx}/{total}] Re-scraping URL: {url}")
            
            try:
                # Same exact process we use for new articles:
                full_content = scrape_article_content(url)
                
                if full_content:
                    enhanced_html = enhance_article_html(full_content)
                    final_html = _sanitize_content(enhanced_html)
                    
                    if final_html:
                        # Success! Update the database.
                        article.content = final_html
                        success_count += 1
                        logger.info("  -> Successfully updated with perfect HTML!")
                    else:
                        logger.warning("  -> Output HTML was empty.")
                else:
                    logger.warning("  -> Extractor couldn't scrape the article text.")
                
            except Exception as e:
                logger.error(f"  -> Fatal error updating {url}: {e}")

            # Commit in batches of 50 to prevent huge memory spikes
            if idx % 50 == 0:
                logger.info("  [!] Committing batch to database...")
                db.session.commit()
                
            # Sleep slightly to not hammer the servers we are scraping
            time.sleep(1)

        # Final commit for the remaining articles
        db.session.commit()
        logger.info(f"Done! Successfully completely restored {success_count} out of {total} articles with HTML tags.")

if __name__ == "__main__":
    update_existing_articles()
