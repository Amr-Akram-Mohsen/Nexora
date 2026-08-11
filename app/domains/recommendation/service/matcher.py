import re
import logging
from datetime import datetime, timedelta
from app.core.extensions import db
from app.domains.content.models import Article, Content
from app.domains.product.models import Product
from app.domains.product.service.options import get_item_load_options
logger = logging.getLogger(__name__)
BATCH_SIZE = 100
MIN_SCORE = 2
MAX_LINKS_PER_ARTICLE = 5
REPROCESS_AFTER = timedelta(days=7)
def _tokenize(text: str) -> set[str]:
    text = text.lower()
    words = re.findall('[a-z0-9]+', text)
    return {w for w in words if len(w) >= 3}
def _score_match(article_tokens: set[str], product: Product) -> int:
    score = 0
    item_name_lower = product.name.lower()
    brand_name_lower = product.brand.name.lower()
    cat_name_lower = product.category.name.lower() if product.category else ''
    article_text = ' '.join(article_tokens)
    if item_name_lower in article_text:
        score += 3
    if brand_name_lower in article_text and len(brand_name_lower) >= 3:
        score += 2
    if cat_name_lower and cat_name_lower in article_text:
        score += 1
    if score < 3:
        model_keywords = [w for w in re.findall('[a-z0-9]+', item_name_lower) if len(w) >= 4 and w != brand_name_lower]
        keyword_hits = sum((1 for kw in model_keywords if kw in article_tokens))
        score += min(keyword_hits, 3)
    return score
def match_articles_to_items(dry_run: bool=False, since: datetime | None=None) -> int:
    logger.info('[Matcher] Starting article-to-product matching (batch_size=%d, min_score=%d)…', BATCH_SIZE, MIN_SCORE)
    products = Product.query.options(*get_item_load_options('minimal')).all()
    if not products:
        logger.info('[Matcher] No products found. Nothing to match against.')
        return 0
    logger.info('[Matcher] Loaded %d products to match against.', len(products))
    total_links = 0
    page = 0
    while True:
        from app.domains.content.service.query.utils import get_unmatched_articles_query
        cutoff = datetime.utcnow() - REPROCESS_AFTER
        article_q = get_unmatched_articles_query(cutoff=cutoff, since=since, session=db.session)
        batch = article_q.offset(page * BATCH_SIZE).limit(BATCH_SIZE).all()
        if not batch:
            break
        logger.info('[Matcher] Processing batch %d (%d articles)…', page + 1, len(batch))
        for article in batch:
            search_text = f'{article.title} {article.description or ''}'
            article_tokens = _tokenize(search_text)
            current_links = len(article.linked_products)
            batch_links = 0
            for product in products:
                if current_links + batch_links >= MAX_LINKS_PER_ARTICLE:
                    break
                if product in article.linked_products:
                    continue
                score = _score_match(article_tokens, product)
                if score >= MIN_SCORE:
                    article.linked_products.append(product)
                    batch_links += 1
                    total_links += 1
                    logger.debug("[Matcher] score=%d  '%s'  <->  '%s'", score, product.name, article.title[:60])
            article.last_matched_at = datetime.utcnow()
        if not dry_run:
            try:
                db.session.commit()
                logger.info('[Matcher] Batch %d committed — %d total links so far.', page + 1, total_links)
            except Exception:
                db.session.rollback()
                logger.exception('[Matcher] Error committing batch %d.', page + 1)
        page += 1
    logger.info('[Matcher] Done. Created %d new article-product links.', total_links)
    return total_links