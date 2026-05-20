"""
Abstract base class for all source-specific product parsers.

Architecture:
    Raw input (HTML / JSON / API response)
        ↓
    ConcreteParser(BaseParser).parse(raw_dict)
        ↓
    ParsedProduct   ←── shared schema, source-agnostic
        ↓
    ProductInserter → SQLAlchemy → Database

To add a new source, subclass BaseParser, set source_slug, and implement parse().
The ProductInserter requires no changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.integrations.commercial.schema import ParsedProduct


class BaseParser(ABC):
    """
    Contract every source-specific parser must fulfil.

    Concrete parsers receive a raw product dict (one entry from the
    batch JSON file) and must return a fully populated ParsedProduct,
    or None when the entry cannot be parsed (missing title, etc.).
    """

    #: Must be overridden in every subclass.  Matches the Store.slug in DB.
    source_slug: str

    @abstractmethod
    def parse(self, raw: dict) -> Optional[ParsedProduct]:
        """
        Transform a raw product entry into a normalized ParsedProduct.

        Args:
            raw: One product dict from the batch JSON file.

        Returns:
            ParsedProduct on success, None if the entry must be skipped.
        """
        ...
