# app/utils/matcher.py
"""
Utility for bridging Articles and Items.
Matches products to articles based on keyword matching in titles.
"""
import logging
from app.models import db, Article, Item

logger = logging.getLogger(__name__)

def match_articles_to_items():
    """
    Scans recent articles and attempts to link them to existing items
    based on keyword matching.
    """
    logger.info("[Matcher] Starting article-to-item matching...")
    
    # 1. Fetch all items (limited set for now, or indexed)
    items = Item.query.all()
    if not items:
        logger.info("[Matcher] No items found to match against.")
        return 0

    # 2. Fetch articles that don't have linked items yet (or all recent ones)
    articles = Article.query.all() 
    
    total_links = 0
    
    for article in articles:
        title_lower = article.title.lower()
        
        for item in items:
            # We check if the item name (or significant part of it) is in the title.
            # For better accuracy, we can check for brand + item name parts.
            brand_name = item.brand.name.lower()
            item_name = item.name.lower()
            
            # Match if: 
            # 1. Full item name is in title
            # OR 2. Brand + specific model name (e.g. "Apple" and "iPhone 16")
            if item_name in title_lower:
                if item not in article.linked_items:
                    article.linked_items.append(item)
                    total_links += 1
                    logger.info(f"[Matcher] Linked: '{item.name}' <-> '{article.title[:50]}...'")
            
            elif brand_name in title_lower and any(word in title_lower for word in item_name.split() if len(word) > 3):
                # Heuristic: Brand is present and one significant word from the product name is present
                 if item not in article.linked_items:
                    article.linked_items.append(item)
                    total_links += 1
                    logger.info(f"[Matcher] Linked (Heuristic): '{item.name}' <-> '{article.title[:50]}...'")

    try:
        db.session.commit()
        logger.info(f"[Matcher] Finished. Created {total_links} links.")
        return total_links
    except Exception:
        db.session.rollback()
        logger.exception("[Matcher] Error saving links.")
        return 0
