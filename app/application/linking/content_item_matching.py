# app/application/linking/content_item_matching.py
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, select

from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.item.models import Item
from app.domains.relationships import content_items
from app.domains.recommendation.ranking import score_content_item_link

logger = logging.getLogger(__name__)


def get_candidate_items_for_content(content, session):
    """
    Get a candidate pool of items for a given content.
    Includes items in the same category or belonging to the same brand.
    """
    brand_ids = [b.id for b in content.brands] if content.brands else []
    conditions = []
    if content.category_id:
        conditions.append(Item.category_id == content.category_id)
    if brand_ids:
        conditions.append(Item.brand_id.in_(brand_ids))

    if not conditions:
        return []

    stmt = select(Item).where(or_(*conditions))
    return session.execute(stmt).scalars().all()


def get_candidate_contents_for_item(item, session):
    """
    Get a candidate pool of contents for a given item.
    Includes contents in the same category or belonging to the same brand.
    """
    conditions = []
    if item.category_id:
        conditions.append(Content.category_id == item.category_id)

    stmt = select(Content)
    if item.brand_id:
        from app.domains.relationships import content_brands
        stmt = stmt.outerjoin(content_brands, Content.id == content_brands.c.content_id)
        conditions.append(content_brands.c.brand_id == item.brand_id)

    if not conditions:
        return []

    stmt = stmt.where(or_(*conditions)).order_by(Content.published_at.desc()).limit(1000)
    return session.execute(stmt).scalars().all()


def run_content_item_matching(
    batch_size: int = 100,
    score_threshold: float = 4.0,
    since_days: int | None = None,
    session=None,
) -> dict:
    """
    Orchestration workflow for cross-domain Content-Item matching.

    Looks for recently ingested/created Content and Item records, evaluates
    matches using the domain's weighted scoring engine, and populates the
    content_items association table.

    Args:
        batch_size: Size of batches for processing content records.
        score_threshold: Minimum match score to create a link.
        since_days: Filter contents/items created in the last N days. If None, process all.
        session: Scoped database session. Falls back to db.session.

    Returns:
        dict: Summary of the run (processed contents, processed items, matches created).
    """
    if session is None:
        session = db.session

    summary = {
        "processed_contents": 0,
        "processed_items": 0,
        "links_created": 0,
    }

    # Determine cutoff timestamps if since_days is provided
    cutoff = None
    if since_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)

    logger.info(
        f"Starting Content <-> Item matching run (since_days={since_days}, threshold={score_threshold})"
    )

    # ── PASS 1: Process Content against Items ────────────────────────────────
    # Query contents to evaluate
    content_stmt = select(Content).where(Content.is_active == True)
    if cutoff:
        cutoff_naive = datetime.utcnow() - timedelta(days=since_days)
        content_stmt = content_stmt.where(
            or_(Content.ingested_at >= cutoff, Content.ingested_at >= cutoff_naive)
        )

    # Fetch contents page by page
    offset = 0
    while True:
        batch_stmt = content_stmt.offset(offset).limit(batch_size)
        contents = session.execute(batch_stmt).scalars().all()
        if not contents:
            break

        summary["processed_contents"] += len(contents)

        # Pre-fetch existing links for this batch to prevent N+1 queries
        content_ids = [c.id for c in contents]
        existing_links = session.execute(
            select(content_items.c.content_id, content_items.c.item_id)
            .where(content_items.c.content_id.in_(content_ids))
        ).all()
        existing_set = {(row.content_id, row.item_id) for row in existing_links}

        for content in contents:
            candidates = get_candidate_items_for_content(content, session)
            for item in candidates:
                if (content.id, item.id) in existing_set:
                    continue

                score = score_content_item_link(content, item)
                if score >= score_threshold:
                    content.linked_items.append(item)
                    existing_set.add((content.id, item.id))
                    summary["links_created"] += 1
                    content_title = content.title or "Untitled"
                    item_name = item.name or "Unnamed"
                    logger.info(
                        f"Matched Content '{content_title[:30]}' <-> Item '{item_name[:30]}' (Score: {score:.2f})"
                    )

        session.commit()
        offset += batch_size

    # ── PASS 2: Process Items against Contents ──────────────────────────────
    # Query items to evaluate
    item_stmt = select(Item)
    if cutoff:
        cutoff_naive = datetime.utcnow() - timedelta(days=since_days)
        item_stmt = item_stmt.where(
            or_(Item.created_at >= cutoff, Item.created_at >= cutoff_naive)
        )

    items = session.execute(item_stmt).scalars().all()
    summary["processed_items"] = len(items)

    if items:
        # Pre-fetch existing links for all items in Pass 2
        item_ids = [item.id for item in items]
        existing_links = session.execute(
            select(content_items.c.content_id, content_items.c.item_id)
            .where(content_items.c.item_id.in_(item_ids))
        ).all()
        existing_set = {(row.content_id, row.item_id) for row in existing_links}

        for item in items:
            candidates = get_candidate_contents_for_item(item, session)
            for content in candidates:
                if (content.id, item.id) in existing_set:
                    continue

                score = score_content_item_link(content, item)
                if score >= score_threshold:
                    content.linked_items.append(item)
                    existing_set.add((content.id, item.id))
                    summary["links_created"] += 1
                    content_title = content.title or "Untitled"
                    item_name = item.name or "Unnamed"
                    logger.info(
                        f"Matched Item '{item_name[:30]}' <-> Content '{content_title[:30]}' (Score: {score:.2f})"
                    )

        session.commit()

    logger.info(f"Matching run complete: {summary}")
    return summary
