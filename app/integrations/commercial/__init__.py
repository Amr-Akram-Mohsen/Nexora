"""
app/integrations/commercial

Manual product ingestion pipeline for commercial sources.

Architecture:
    Raw batch JSON
      ↓
    BaseParser subclass  (one per source)
      ↓
    ParsedProduct        (normalized in-memory dataclass)
      ↓
    ProductInserter      (source-agnostic DB insertion)
      ↓
    SQLAlchemy / Database

Currently supported sources:
    - AliExpress  →  app.integrations.commercial.aliexpress.AliExpressParser

To add a new source:
    1. Create app/integrations/commercial/<source>/parser.py
       with a class that extends BaseParser and implements parse().
    2. Register the parser in run_import.PARSER_REGISTRY.
    3. The inserter requires no changes.

Entry point:
    python -m app.integrations.commercial.run_import [--batch FILE] [--dry-run]
"""
