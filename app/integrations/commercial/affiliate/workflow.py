"""
Affiliate link generation workflow module.

Independent post-ingestion workflow that queries products in 'scraped' or 'validated' state,
generates tracking affiliate links, and advances status to 'ready'.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.extensions import db
from app.domains.product.models import ProductStoreLink, Store, Product
from app.integrations.commercial.affiliate.admitad import generate_admitad_affiliate_url

logger = logging.getLogger("commercial.affiliate.workflow")


def generate_affiliate_links_for_store(
    store_slug: str = "aliexpress",
    session: Optional[Session] = None,
) -> tuple[int, int]:
    """
    Process store links for products where affiliate link has not yet been generated.

    Returns tuple of (updated_count, failed_count).
    """
    if session is None:
        session = db.session

    updated = 0
    failed = 0

    links = (
        session.query(ProductStoreLink)
        .join(Store)
        .filter(
            Store.slug == store_slug,
            (ProductStoreLink.affiliate_url == ProductStoreLink.original_url)
            | (ProductStoreLink.affiliate_url.is_(None)),
        )
        .all()
    )

    logger.info("[AffiliateWorkflow] Found %d links needing affiliate URL generation for store '%s'", len(links), store_slug)
    now = datetime.now(timezone.utc)

    for link in links:
        try:
            if not link.original_url:
                continue

            aff_url = generate_admitad_affiliate_url(
                original_url=link.original_url,
                subid=f"nexora_{link.variant_id}",
            )

            if aff_url and aff_url != link.original_url:
                link.affiliate_url = aff_url
                link.deeplink_generated_at = now
                updated += 1

                # Advance parent product ingestion status from 'scraped'/'validated' to 'ready'
                if link.variant and link.variant.product:
                    prod: Product = link.variant.product
                    if prod.ingestion_status in ("scraped", "validated", "pending"):
                        prod.ingestion_status = "ready"

        except Exception as e:
            logger.exception("[AffiliateWorkflow] Error generating affiliate link for store_link id=%s", link.id)
            failed += 1

    session.flush()
    logger.info("[AffiliateWorkflow] Completed affiliate link generation: updated=%d, failed=%d", updated, failed)
    return updated, failed
