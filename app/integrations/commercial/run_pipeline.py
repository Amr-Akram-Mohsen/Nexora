"""
CLI entry point for running the commercial automated category ingestion pipeline.

Usage:
    python -m app.integrations.commercial.run_pipeline
    python -m app.integrations.commercial.run_pipeline --category "Electronics" --page 1 --dry-run
"""
from __future__ import annotations

import argparse
import sys
import logging

from app.core import create_app
from app.integrations.commercial.pipeline import IngestionPipeline


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("commercial.cli")


def main() -> None:
    parser = argparse.ArgumentParser(description="Nexora Automated Product Ingestion Pipeline")
    parser.add_argument("--category", default="Electronics", help="Root category text (default: Electronics)")
    parser.add_argument("--subcategory", default=None, help="Subcategory text (default: None)")
    parser.add_argument("--page", type=int, default=1, help="Target page number to discover (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Discover and preview without any database writes")
    parser.add_argument("--discover-only", action="store_true", help="Only run URL discovery and enqueueing")
    parser.add_argument("--process-only", action="store_true", help="Only process existing pending queue items")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of product queue items to scrape and process (default: 50)")

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        pipeline = IngestionPipeline(headless=False)
        stats = pipeline.run(
            source_type="category",
            category=args.category,
            subcategory=args.subcategory,
            page=args.page,
            dry_run=args.dry_run,
            discover_only=args.discover_only,
            process_only=args.process_only,
            limit=args.limit,
        )



        print(f"\n[OK] Pipeline completed stats: {stats}\n")
        logger.info("Pipeline completed stats: %s", stats)


if __name__ == "__main__":
    main()


