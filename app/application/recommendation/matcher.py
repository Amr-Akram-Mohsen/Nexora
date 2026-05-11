# app/utils/matcher.py
"""
Article ↔ Item Matcher — Phase 6C
===================================
Links articles to related products based on multi-signal scoring.

Phase 6C improvements over original:
  - Batch pagination instead of loading ALL articles into memory at once
  - Smarter scoring: brand match + category match + multi-keyword model match
  - Tracks `last_matched_at` on Article to skip already-processed articles
    (add this column to Article model via migration if not present)
  - Configurable score threshold to control match quality
  - Dry-run mode for testing without committing
"""
import re
import logging
from datetime import datetime, timedelta
from app.core.extensions import db
from app.domains.content.models import Article, Content
from app.domains.item.models import Item

logger = logging.getLogger(__name__)

# ── Tuning knobs ───────────────────────────────────────────────────────────
BATCH_SIZE      = 100    # articles per DB page
MIN_SCORE       = 2      # minimum score to create a link (higher = stricter)
MAX_LINKS_PER_ARTICLE = 5  # cap links per article to avoid spam
REPROCESS_AFTER = timedelta(days=7)  # re-check articles older than this
# ──────────────────────────────────────────────────────────────────────────


def _tokenize(text: str) -> set[str]:
    """Lowercase, remove punctuation, split into word tokens (len >= 3)."""
    text = text.lower()
    words = re.findall(r"[a-z0-9]+", text)
    return {w for w in words if len(w) >= 3}


def _score_match(article_tokens: set[str], item: Item) -> int:
    """
    Score how well an item matches an article based on multiple signals.

    Scoring:
      +3  — full item name substring found in article title (high confidence)
      +2  — brand name present in article title
      +1  — category name present in article tokens
      +1  — each significant model keyword (len >= 4) present in article tokens
              (capped at +3 to avoid over-scoring long names)

    Returns an integer score; MIN_SCORE is the threshold for linking.
    """
    score = 0
    item_name_lower  = item.name.lower()
    brand_name_lower = item.brand.name.lower()
    cat_name_lower   = item.category.name.lower() if item.category else ""

    article_text = " ".join(article_tokens)

    # Signal 1: full item name in text
    if item_name_lower in article_text:
        score += 3

    # Signal 2: brand name in text
    if brand_name_lower in article_text and len(brand_name_lower) >= 3:
        score += 2

    # Signal 3: category name in tokens
    if cat_name_lower and cat_name_lower in article_text:
        score += 1

    # Signal 4: model keywords (individual significant words from item name)
    if score < 3:   # skip if already high-confidence
        model_keywords = [
            w for w in re.findall(r"[a-z0-9]+", item_name_lower)
            if len(w) >= 4 and w != brand_name_lower
        ]
        keyword_hits = sum(1 for kw in model_keywords if kw in article_tokens)
        score += min(keyword_hits, 3)   # cap at +3

    return score


def match_articles_to_items(
    dry_run: bool = False,
    since: datetime | None = None,
) -> int:
    """
    Scan unmatched (or stale) articles and link them to relevant items.

    Args:
        dry_run:  If True, calculate matches but don't commit to DB.
        since:    Only process articles published after this datetime.
                  Defaults to articles not yet matched or matched > REPROCESS_AFTER ago.

    Returns:
        Number of new article-item links created.
    """
    logger.info("[Matcher] Starting article-to-item matching (batch_size=%d, min_score=%d)…",
                BATCH_SIZE, MIN_SCORE)

    # Load all items once — item count is much smaller than article count
    # and each item is lightweight (name + brand + category only needed)
    items = Item.query.all()
    if not items:
        logger.info("[Matcher] No items found. Nothing to match against.")
        return 0

    logger.info("[Matcher] Loaded %d items to match against.", len(items))

    total_links   = 0
    page          = 0

    while True:
        # ── Build article query with pagination ───────────────────
        cutoff = datetime.utcnow() - REPROCESS_AFTER
        article_q = (
            db.session.query(Article)
            .join(Content, (Content.object_type == "article") & (Content.object_id == Article.id))
            .filter(
                # Either never matched, or matched long enough ago to re-check
                db.or_(
                    Article.last_matched_at.is_(None),
                    Article.last_matched_at < cutoff,
                )
            )
        )
        if since:
            article_q = article_q.filter(Content.published_at >= since)

        batch = article_q.offset(page * BATCH_SIZE).limit(BATCH_SIZE).all()
        if not batch:
            break

        logger.info("[Matcher] Processing batch %d (%d articles)…", page + 1, len(batch))

        for article in batch:
            # Tokenize title + description for matching
            search_text  = f"{article.title} {article.description or ''}"
            article_tokens = _tokenize(search_text)

            current_links = len(article.linked_items)
            batch_links   = 0

            for item in items:
                if current_links + batch_links >= MAX_LINKS_PER_ARTICLE:
                    break
                if item in article.linked_items:
                    continue

                score = _score_match(article_tokens, item)
                if score >= MIN_SCORE:
                    article.linked_items.append(item)
                    batch_links += 1
                    total_links += 1
                    logger.debug(
                        "[Matcher] score=%d  '%s'  <->  '%s'",
                        score, item.name, article.title[:60],
                    )

            # Stamp the article so we don't re-process it next run
            article.last_matched_at = datetime.utcnow()

        if not dry_run:
            try:
                db.session.commit()
                logger.info("[Matcher] Batch %d committed — %d total links so far.",
                            page + 1, total_links)
            except Exception:
                db.session.rollback()
                logger.exception("[Matcher] Error committing batch %d.", page + 1)

        page += 1

    logger.info("[Matcher] Done. Created %d new article-item links.", total_links)
    return total_links

