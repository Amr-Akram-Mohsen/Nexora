# app/application/linking/content_item_matching.py
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, select

from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.item.models import Item
from app.domains.relationships import content_items
from app.domains.recommendation.ranking import score_content_item_link
from app.domains.item.service.query import (
    get_candidate_items_for_content,
    get_items_for_matching,
    get_existing_content_item_links_by_items,
)
from app.domains.content.service.query.filtering import (
    get_candidate_contents_for_item,
    get_contents_for_matching_batch,
    get_existing_content_item_links_by_contents,
)

logger = logging.getLogger(__name__)





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
    cutoff_naive = None
    if cutoff:
        cutoff_naive = datetime.utcnow() - timedelta(days=since_days)

    # Fetch contents page by page
    offset = 0
    while True:
        contents = get_contents_for_matching_batch(
            offset, batch_size, cutoff=cutoff, cutoff_naive=cutoff_naive, session=session
        )
        if not contents:
            break

        summary["processed_contents"] += len(contents)

        # Pre-fetch existing links for this batch to prevent N+1 queries
        content_ids = [c.id for c in contents]
        existing_links = get_existing_content_item_links_by_contents(content_ids, session)
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
    items = get_items_for_matching(cutoff=cutoff, cutoff_naive=cutoff_naive, session=session)
    summary["processed_items"] = len(items)

    if items:
        # Pre-fetch existing links for all items in Pass 2
        item_ids = [item.id for item in items]
        existing_links = get_existing_content_item_links_by_items(item_ids, session)
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
