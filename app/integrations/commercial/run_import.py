"""
run_import.py — CLI entry point for the AliExpress product ingestion pipeline.

Usage (from project root, inside Flask app context):
    python -m app.integrations.commercial.run_import
    python -m app.integrations.commercial.run_import --batch path/to/other_batch.json
    python -m app.integrations.commercial.run_import --dry-run

Workflow:
    Load batch JSON
    run_import.py — CLI entry point for the commercial product ingestion pipeline.

    This module is store-agnostic: parsers are registered in
    `app.integrations.commercial.registry` and per-store raw HTML files are
    expected under `app/integrations/commercial/<store>/raw_html/p{index}.html`.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from app.integrations.commercial import registry
from app.integrations.commercial import io as commercial_io

# Use a logger outside the app.* namespace so it always reaches the
# root handler set up by basicConfig, bypassing Flask's ingestion filters.
logger = logging.getLogger("commercial.import")

# Default batch file location (keeps prior default for backwards compat)
_DEFAULT_BATCH = Path(__file__).parent / "aliexpress" / "products_batch.json"


def _load_batch(path: Path) -> list[dict]:
    if not path.exists():
        logger.error("Batch file not found: %s", path)
        sys.exit(1)
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        logger.error("Batch file must contain a JSON array.")
        sys.exit(1)
    return data


def run_import(batch_path: Path, dry_run: bool = False, store_override: Optional[str] = None) -> None:
    """Main import loop. Must be called inside a Flask application context."""
    from app.core.extensions import db
    from app.integrations.commercial.inserter import ProductInserter

    batch = _load_batch(batch_path)
    logger.info("[Import] Loaded %d entries from %s", len(batch), batch_path)

    # Group entries by store so we instantiate each parser once
    parsers: dict[str, object] = {}

    inserted = 0
    skipped = 0
    errors = 0

    for idx, raw in enumerate(batch, start=1):
        store_slug = (store_override or raw.get("store", "")).lower().strip()
        if not store_slug:
            logger.warning(
                "[Import] Entry %d has no 'store' field and no --store specified — skipping.",
                idx,
            )
            skipped += 1
            continue

        # Load any per-store raw HTML file p{index}.html
        html_fields = commercial_io.load_html_for_product(store_slug, idx)
        raw.update(html_fields)

        # Skip template placeholders (checked after resolution)
        if "PASTE" in str(raw.get("product_info_html", "")):
            logger.info("[Import] Entry %d looks like a template placeholder — skipping.", idx)
            skipped += 1
            continue

        try:
            if store_slug not in parsers:
                parsers[store_slug] = registry.get_parser_instance(store_slug)
            parser = parsers[store_slug]
        except ValueError as exc:
            logger.warning("[Import] Entry %d: %s — skipping.", idx, exc)
            skipped += 1
            continue

        parsed = parser.parse(raw)
        if parsed is None:
            logger.warning(
                "[Import] Entry %d could not be parsed (store=%s url=%s).",
                idx,
                store_slug,
                raw.get("product_url", ""),
            )
            errors += 1
            continue

        if dry_run:
            logger.info(
                "[Import][DRY-RUN] Would insert: '%s' | brand=%s | category=%s | variants=%d | images=%d",
                parsed.name,
                parsed.brand_name,
                parsed.category_name,
                len(parsed.variants),
                len(parsed.images),
            )
            inserted += 1
            continue

        inserter = ProductInserter(db.session)
        product = inserter.insert(parsed)

        if product is not None:
            db.session.commit()
            logger.info("[Import] Inserted: '%s' (id=%s, slug=%s)", product.name, product.id, product.slug)
            inserted += 1
        else:
            # None means duplicate (already logged) or a DB exception (inserter logs it).
            db.session.rollback()
            skipped += 1

    logger.info("[Import] Done — inserted=%d  skipped/duplicate=%d  errors=%d", inserted, skipped, errors)
    print(f"\n[OK] Import complete: {inserted} inserted, {skipped} skipped/duplicate, {errors} errors.\n")


def _build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Import products from a batch JSON file into the database.")
    ap.add_argument("--batch", type=Path, default=_DEFAULT_BATCH, help=f"Path to the batch JSON file (default: {_DEFAULT_BATCH})")
    ap.add_argument("--dry-run", action="store_true", help="Parse and log products without writing to the database.")
    ap.add_argument("--store", type=str, help="Optional: force a store slug for all entries in the batch.")
    return ap


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()

    # Load .env BEFORE importing create_app.
    from dotenv import load_dotenv

    load_dotenv()

    from app.core import create_app

    app = create_app()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%H:%M:%S")

    with app.app_context():
        run_import(batch_path=args.batch, dry_run=args.dry_run, store_override=args.store)


# with app.app_context():
#     run_import(batch_path=args.batch, dry_run=args.dry_run)

