"""
run_import.py — CLI entry point for the AliExpress product ingestion pipeline.

Usage (from project root, inside Flask app context):
    python -m app.integrations.commercial.run_import
    python -m app.integrations.commercial.run_import --batch path/to/other_batch.json
    python -m app.integrations.commercial.run_import --dry-run

Workflow:
    Load batch JSON
      → iterate products
      → AliExpressParser  →  ParsedProduct
      → ProductInserter   →  DB models
      → db.session.commit()

Adding a new source later:
    1. Create a parser in app/integrations/commercial/<source>/parser.py
    2. Register it in PARSER_REGISTRY below.
    3. No other changes needed.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Use a logger outside the app.* namespace so it always reaches the
# root handler set up by basicConfig, bypassing Flask's ingestion filters.
logger = logging.getLogger("commercial.import")

# Default batch file location
_DEFAULT_BATCH = (
    Path(__file__).parent / "data" / "products_batch.json"
)

# Registry maps the "store" field in the JSON to the correct parser class.
# Add new parsers here as you build them — nothing else changes.
PARSER_REGISTRY: dict[str, str] = {
    "aliexpress": "app.integrations.commercial.aliexpress.parser.AliExpressParser",
}


def _load_parser(store_slug: str):
    """Dynamically import and instantiate the parser for a given store slug."""
    dotted = PARSER_REGISTRY.get(store_slug)
    if not dotted:
        raise ValueError(f"No parser registered for store '{store_slug}'")
    module_path, class_name = dotted.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()


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


_HTML_FIELDS = ("product_info_html", "specifications_html")


def _resolve_html_fields(raw: dict, batch_dir: Path) -> dict:
    """
    For each HTML field: if the value looks like a file path (ends with .html
    and is not a long HTML string), load the file content from disk.
    Paths are resolved relative to the batch JSON file's directory.
    """
    result = dict(raw)
    for field in _HTML_FIELDS:
        value = result.get(field, "")
        if not value:
            continue
        # Treat it as a file path if it ends with .html and has no angle brackets
        stripped = value.strip()
        if stripped.endswith(".html") and "<" not in stripped:
            candidate = (batch_dir / stripped).resolve()
            if candidate.exists():
                result[field] = candidate.read_text(encoding="utf-8")
            else:
                logger.warning(
                    "[Import] HTML file not found: %s (field=%s)", candidate, field
                )
                result[field] = ""
    return result


def run_import(batch_path: Path, dry_run: bool = False) -> None:
    """
    Main import loop.  Must be called inside a Flask application context
    (handled by __main__ block below, or by the Flask CLI command).
    """
    from app.core.extensions import db
    from app.integrations.commercial.inserter import ProductInserter

    batch = _load_batch(batch_path)
    batch_dir = batch_path.resolve().parent
    logger.info("[AliExpress Import] Loaded %d entries from %s", len(batch), batch_path)

    # Group entries by store so we instantiate each parser once
    parsers: dict[str, object] = {}

    inserted = 0
    skipped = 0
    errors = 0

    for idx, raw in enumerate(batch, start=1):
        store_slug: str = raw.get("store", "").lower().strip()
        if not store_slug:
            logger.warning("[Import] Entry %d has no 'store' field — skipping.", idx)
            skipped += 1
            continue

        # Resolve file-path HTML fields before any other processing
        raw = _resolve_html_fields(raw, batch_dir)

        # Skip template placeholders (checked after resolution)
        if "PASTE" in str(raw.get("product_info_html", "")):
            logger.info("[Import] Entry %d looks like a template placeholder — skipping.", idx)
            skipped += 1
            continue

        try:
            if store_slug not in parsers:
                parsers[store_slug] = _load_parser(store_slug)
            parser = parsers[store_slug]
        except ValueError as exc:
            logger.warning("[Import] Entry %d: %s — skipping.", idx, exc)
            skipped += 1
            continue

        parsed = parser.parse(raw)
        if parsed is None:
            logger.warning(
                "[Import] Entry %d could not be parsed (store=%s url=%s).",
                idx, store_slug, raw.get("product_url", ""),
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
        item = inserter.insert(parsed)

        if item is not None:
            db.session.commit()
            logger.info(
                "[Import] Inserted: '%s' (id=%s, slug=%s)",
                item.name, item.id, item.slug,
            )
            inserted += 1
        else:
            # None means duplicate (already logged) or a DB exception (inserter logs it).
            db.session.rollback()
            skipped += 1

    logger.info(
        "[Import] Done — inserted=%d  skipped/duplicate=%d  errors=%d",
        inserted, skipped, errors,
    )
    print(
        f"\n[OK] Import complete: {inserted} inserted, {skipped} skipped/duplicate, {errors} errors.\n"
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Import AliExpress products from a batch JSON file into the database."
    )
    ap.add_argument(
        "--batch",
        type=Path,
        default=_DEFAULT_BATCH,
        help=f"Path to the batch JSON file (default: {_DEFAULT_BATCH})",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and log products without writing to the database.",
    )
    return ap


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()

    # Load .env BEFORE importing create_app.
    # Config.SQLALCHEMY_DATABASE_URI is evaluated at class-definition time
    # (when config.py is first imported), so DATABASE_URL must already be in
    # os.environ at that point, otherwise it falls back to the SQLite default.
    from dotenv import load_dotenv
    load_dotenv()

    from app.core import create_app

    app = create_app()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )

    with app.app_context():
        run_import(batch_path=args.batch, dry_run=args.dry_run)

