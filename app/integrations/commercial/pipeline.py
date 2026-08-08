"""
IngestionPipeline — main end-to-end orchestration pipeline.

Coordinates: Discovery → Queue → Scraper → Parser → Validation → Inserter → Search Indexer
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.core.extensions import db
from app.domains.product.models import Product
from app.integrations.commercial.models import ProductDiscoveryQueue
from app.integrations.commercial import queue
from app.integrations.commercial.inserter import ProductInserter
from app.integrations.commercial.validation import validate_parsed_product
from app.integrations.commercial.aliexpress.parser import AliExpressParser
from app.integrations.commercial.aliexpress.scraper import AliExpressScraper
from app.integrations.commercial.aliexpress.discovery import (
    AliExpressCategoryDiscovery,
    DiscoveredURL,
)

from app.shared.utils.logging import (
    log_commercial_discovery_start,
    log_commercial_discovery_success,
    log_commercial_enqueue,
    log_commercial_scrape_start,
    log_commercial_scrape_success,
    log_commercial_scrape_failed,
    log_commercial_ingest_success,
    log_commercial_pipeline_done,
    log_commercial_captcha,
    log_commercial_retry,
)

logger = logging.getLogger("app.commercial.pipeline")


class IngestionPipeline:
    """End-to-end commercial product ingestion pipeline with separate discovery & queue processing phases."""

    def __init__(self, headless: bool = False) -> None:
        self.headless = headless
        self.parser = AliExpressParser()

    def discover_urls(
        self,
        source_type: str = "category",
        *,
        category: Optional[str] = "Electronics",
        subcategory: Optional[str] = None,
        page: int = 1,
        dry_run: bool = False,
        session: Optional[Session] = None,
    ) -> dict[str, int]:
        """
        Execute category URL discovery phase and enqueue discovered links.
        `dry_run`: If True, discovers URLs and previews results with ZERO database writes.
        """
        if session is None:
            session = db.session

        stats = {"discovered": 0, "enqueued": 0, "duplicates": 0}

        target_category = category or "Electronics"
        log_commercial_discovery_start(logger, source_type, target_category, page)

        disc = AliExpressCategoryDiscovery(headless=self.headless)
        discovered_urls = disc.discover(
            root_category_text=target_category,
            subcategory_text=subcategory,
            page_num=page,
        )

        stats["discovered"] = len(discovered_urls)
        log_commercial_discovery_success(logger, source_type, target_category, len(discovered_urls), page)

        if dry_run:
            print(f"\n========================================================")
            print(f"[IngestionPipeline] DRY-RUN DISCOVERY COMPLETE (Zero DB writes)")
            print(f"========================================================")
            print(f"Discovered {len(discovered_urls)} products for source '{source_type}':")
            for idx, item in enumerate(discovered_urls, 1):
                print(f"  [{idx}/{len(discovered_urls)}] {item.url}")
            print(f"========================================================")
            try:
                session.rollback()
            except Exception:
                pass
            return stats

        if discovered_urls:
            enqueued_cnt, dup_cnt = queue.enqueue_batch(discovered_urls, session=session)
            stats["enqueued"] = enqueued_cnt
            stats["duplicates"] = dup_cnt
            session.commit()
            log_commercial_enqueue(logger, enqueued_cnt, dup_cnt)

        return stats

    def process_queue(
        self,
        limit: int = 50,
        store_slug: str = "aliexpress",
        session: Optional[Session] = None,
    ) -> dict[str, int]:
        """
        Process pending URLs from ProductDiscoveryQueue one by one.
        Commits to DB after EVERY individual product page is scraped and inserted.
        `limit`: Maximum number of pending items to process in this run.
        """
        if session is None:
            session = db.session

        stats = {
            "claimed": 0,
            "scraped": 0,
            "inserted": 0,
            "duplicates": 0,
            "failed": 0,
            "skipped": 0,
        }

        claimed_entries = queue.claim_pending(batch_size=limit, store_slug=store_slug, session=session)
        session.commit()
        stats["claimed"] = len(claimed_entries)

        if not claimed_entries:
            logger.info("[COMMERCIAL][QUEUE] No pending items in queue to scrape.")
            return stats

        scraper = AliExpressScraper(headless=self.headless)
        inserter = ProductInserter(session)

        # Scrape & process each item isolated with individual DB commit
        for entry in claimed_entries:
            try:
                log_commercial_scrape_start(logger, entry.url)

                scrape_res = scraper.scrape(entry.url)
                if scrape_res.captcha_detected:
                    queue.mark_skipped(entry, "Captcha wall encountered", session=session)
                    log_commercial_scrape_failed(logger, entry.url, "Captcha wall")
                    stats["skipped"] += 1
                    session.commit()
                    continue

                if scrape_res.product_removed:
                    queue.mark_skipped(entry, "Product removed or 404", session=session)
                    log_commercial_scrape_failed(logger, entry.url, "Product removed / 404")
                    stats["skipped"] += 1
                    session.commit()
                    continue

                if not scrape_res.success or not scrape_res.html:
                    queue.mark_failed(entry, scrape_res.error or "Scrape failed", session=session)
                    log_commercial_scrape_failed(logger, entry.url, scrape_res.error or "Scrape failed")
                    stats["failed"] += 1
                    session.commit()
                    continue

                stats["scraped"] += 1
                queue.mark_scraped(entry, session=session)

                # PARSE
                raw_payload = {
                    "store": entry.store_slug,
                    "product_url": entry.url,
                    "affiliate_url": entry.url,
                    "html": scrape_res.html,
                }
                parsed = self.parser.parse_with_variants(
                    raw=raw_payload,
                    variant_combinations=scrape_res.variant_combinations,
                )

                if not parsed:
                    queue.mark_failed(entry, "Parser returned None", session=session)
                    log_commercial_scrape_failed(logger, entry.url, "Parser returned None")
                    stats["failed"] += 1
                    session.commit()
                    continue

                log_commercial_scrape_success(logger, entry.url, parsed.name, len(parsed.variants), len(parsed.images))

                # Attach discovery metadata
                parsed.discovery_source = entry.source_type
                parsed.discovery_keyword = entry.keyword
                parsed.discovery_category_path = entry.category_path

                # VALIDATE
                val_res = validate_parsed_product(parsed)
                if not val_res.is_valid:
                    queue.mark_failed(entry, f"Validation failed: {', '.join(val_res.errors)}", session=session)
                    stats["failed"] += 1
                    session.commit()
                    continue

                # INSERT
                product = inserter.insert(parsed)
                if product is None:
                    queue.mark_duplicate(entry, session=session)
                    stats["duplicates"] += 1
                    session.commit()
                    continue

                # POST-INSERT LIFECYCLE UPDATE & COMMIT FOR THIS INDIVIDUAL PRODUCT
                product.ingestion_status = "scraped"
                product.scrape_status = "success"
                product.last_scraped_at = datetime.now(timezone.utc)
                product.scrape_errors = val_res.warnings if val_res.warnings else None

                queue.mark_inserted(entry, product.id, session=session)
                session.commit()
                stats["inserted"] += 1
                log_commercial_ingest_success(logger, product.id, product.name, entry.store_slug, parsed.store_link.price, parsed.store_link.currency)

            except Exception as ex:
                logger.exception("[COMMERCIAL][ERROR] Exception processing entry id=%s", entry.id)
                session.rollback()
                queue.mark_failed(entry, str(ex), session=session)
                stats["failed"] += 1
                session.commit()

        return stats

    def run(
        self,
        source_type: str = "category",
        *,
        category: Optional[str] = "Electronics",
        subcategory: Optional[str] = None,
        page: int = 1,
        dry_run: bool = False,
        discover_only: bool = False,
        process_only: bool = False,
        limit: int = 50,
        session: Optional[Session] = None,
    ) -> dict[str, int]:
        """
        Orchestrate pipeline execution:
        - `discover_only`: Only runs URL discovery & enqueueing.
        - `process_only`: Only runs product page scraping & insertion up to `limit`.
        - Default: Runs discovery followed by queue processing up to `limit`.
        """
        combined_stats = {
            "discovered": 0,
            "enqueued": 0,
            "duplicates": 0,
            "claimed": 0,
            "scraped": 0,
            "inserted": 0,
            "failed": 0,
            "skipped": 0,
        }

        try:
            if not process_only:
                disc_stats = self.discover_urls(
                    source_type=source_type,
                    category=category,
                    subcategory=subcategory,
                    page=page,
                    dry_run=dry_run,
                    session=session,
                )
                combined_stats.update(disc_stats)

            if dry_run or discover_only:
                log_commercial_pipeline_done(logger, combined_stats)
                return combined_stats

            proc_stats = self.process_queue(
                limit=limit,
                store_slug="aliexpress",
                session=session,
            )
            combined_stats.update(proc_stats)

        except Exception as e:
            logger.exception("[COMMERCIAL][ERROR] Global failure in IngestionPipeline.run")

        log_commercial_pipeline_done(logger, combined_stats)
        return combined_stats


