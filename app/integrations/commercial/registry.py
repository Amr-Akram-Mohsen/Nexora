"""
Parser registry for commercial integrations.

Store parsers can be registered as either a dotted import path (string)
or as the parser class itself. `get_parser_instance` returns an instantiated
parser for the given store slug.

This centralises parser discovery so `run_import` remains thin and
source-agnostic.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Type


_registry: Dict[str, Any] = {
    # Keep the existing mapping for backwards compatibility.
    "aliexpress": "app.integrations.commercial.aliexpress.parser.AliExpressParser",
}


def register(store_slug: str, parser: Any) -> None:
    """Register a parser for `store_slug`.

    `parser` can be either a dotted-path string or the parser class itself.
    """
    _registry[store_slug] = parser


def _load_dotted(dotted: str) -> Type:
    module_path, class_name = dotted.rsplit(".", 1)
    module = import_module(module_path)
    return getattr(module, class_name)


def get_parser_instance(store_slug: str):
    """Return an instantiated parser for `store_slug`.

    Raises `ValueError` when no parser is registered for the slug.
    """
    val = _registry.get(store_slug)
    if not val:
        raise ValueError(f"No parser registered for store '{store_slug}'")
    if isinstance(val, str):
        cls = _load_dotted(val)
        # cache the class for faster subsequent lookups
        _registry[store_slug] = cls
    else:
        cls = val
    return cls()


def get_registered_slugs() -> list[str]:
    return list(_registry.keys())
