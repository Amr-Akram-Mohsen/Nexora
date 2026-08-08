"""
Product Discovery Queue operations.

Provides idempotent URL enqueuing, atomic pending-claim, and lifecycle status updates
for URLs undergoing the discovery → scrape → insert ingestion process.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional, Sequence

from sqlalchemy.orm import Session

from app.integrations.commercial.models import ProductDiscoveryQueue
from app.integrations.commercial.aliexpress.utils import normalize_url

if TYPE_CHECKING:
    from app.integrations.commercial.aliexpress.discovery import DiscoveredURL

logger = logging.getLogger("commercial.queue")


def enqueue_url(
    url: str,
    source_type: str,
    *,
    store_slug: str = "aliexpress",
    keyword: Optional[str] = None,
    category_path: Optional[str] = None,
    subcategory: Optional[str] = None,
    raw_metadata: Optional[dict] = None,
    session: Session,
) -> Optional[ProductDiscoveryQueue]:
    """
    Enqueue a single URL into ProductDiscoveryQueue idempotently.

    Returns the new ProductDiscoveryQueue entry, or None if the URL was already queued.
    """
    if not url:
        return None

    norm_url = normalize_url(url)

    # Deduplication is keyed on normalized_url so different raw URLs for the
    # same product (e.g. ar. vs www. subdomain) are only enqueued once.
    existing = session.query(ProductDiscoveryQueue).filter_by(normalized_url=norm_url).first()
    if existing:
        logger.debug(
            "[DiscoveryQueue] Duplicate — raw_url=%s  normalized_url=%s  existing_id=%s",
            url, norm_url, existing.id,
        )
        return None

    entry = ProductDiscoveryQueue(
        url=url,               # raw URL — stored exactly as discovered, never normalized
        normalized_url=norm_url,  # canonical URL — used only as deduplication key
        store_slug=store_slug,
        source_type=source_type,
        keyword=keyword,
        category_path=category_path,
        subcategory=subcategory,
        status="pending",
        raw_metadata=raw_metadata,
    )
    session.add(entry)
    session.flush()
    logger.info(
        "[DiscoveryQueue] Enqueued id=%s  raw_url=%s  normalized_url=%s",
        entry.id, url, norm_url,
    )
    return entry


def enqueue_batch(
    discovered_urls: Sequence["DiscoveredURL"],
    session: Session,
) -> tuple[int, int]:
    """
    Enqueue a list of DiscoveredURL objects into the queue.

    Returns a tuple of (enqueued_count, duplicate_count).
    """
    enqueued = 0
    duplicates = 0

    for disc in discovered_urls:
        res = enqueue_url(
            url=disc.url,
            source_type=disc.source_type,
            store_slug=disc.store_slug,
            keyword=disc.keyword,
            category_path=disc.category_path,
            subcategory=disc.subcategory,
            raw_metadata=disc.raw_metadata,
            session=session,
        )
        if res is not None:
            enqueued += 1
        else:
            duplicates += 1

    return enqueued, duplicates


def claim_pending(
    batch_size: int = 50,
    store_slug: Optional[str] = None,
    session: Session = None,
) -> list[ProductDiscoveryQueue]:
    """
    Claim up to `batch_size` pending entries from the queue by updating status to 'scraping'.

    Returns the list of claimed ProductDiscoveryQueue items.
    """
    query = session.query(ProductDiscoveryQueue).filter_by(status="pending")
    if store_slug:
        query = query.filter_by(store_slug=store_slug)

    entries = query.order_by(ProductDiscoveryQueue.discovered_at.asc()).limit(batch_size).all()
    now = datetime.now(timezone.utc)

    for entry in entries:
        entry.status = "scraping"
        entry.last_attempted_at = now

    session.flush()
    logger.info("[DiscoveryQueue] Claimed %d pending entries for scraping", len(entries))
    return entries


def mark_scraped(entry: ProductDiscoveryQueue, session: Session) -> None:
    """Mark queue entry as successfully scraped."""
    entry.status = "scraped"
    entry.last_attempted_at = datetime.now(timezone.utc)
    session.flush()


def mark_inserted(
    entry: ProductDiscoveryQueue,
    product_id: int,
    session: Session,
) -> None:
    """Mark queue entry as fully inserted into the products domain."""
    entry.status = "inserted"
    entry.product_id = product_id
    entry.last_attempted_at = datetime.now(timezone.utc)
    session.flush()


def mark_duplicate(entry: ProductDiscoveryQueue, session: Session) -> None:
    """Mark queue entry as a duplicate product at insertion stage."""
    entry.status = "duplicate"
    entry.last_attempted_at = datetime.now(timezone.utc)
    session.flush()


def mark_failed(
    entry: ProductDiscoveryQueue,
    error_message: str,
    session: Session,
) -> None:
    """Mark queue entry as failed, incrementing attempt counter."""
    entry.status = "failed"
    entry.attempts = (entry.attempts or 0) + 1
    entry.error_message = error_message
    entry.last_attempted_at = datetime.now(timezone.utc)
    session.flush()


def mark_skipped(
    entry: ProductDiscoveryQueue,
    reason: str,
    session: Session,
) -> None:
    """Mark queue entry as skipped (e.g. captcha detected, product removed)."""
    entry.status = "skipped"
    entry.error_message = reason
    entry.last_attempted_at = datetime.now(timezone.utc)
    session.flush()


def reset_stale_scraping(
    max_age_minutes: int = 30,
    session: Session = None,
) -> int:
    """
    Reset entries stuck in 'scraping' status back to 'pending' if their last_attempted_at
    is older than max_age_minutes. Handles recovery after process crashes.

    Returns count of reset entries.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    stale_entries = (
        session.query(ProductDiscoveryQueue)
        .filter(
            ProductDiscoveryQueue.status == "scraping",
            ProductDiscoveryQueue.last_attempted_at <= cutoff,
        )
        .all()
    )

    for entry in stale_entries:
        entry.status = "pending"

    session.flush()
    if stale_entries:
        logger.info("[DiscoveryQueue] Reset %d stale 'scraping' entries back to 'pending'", len(stale_entries))
    return len(stale_entries)
