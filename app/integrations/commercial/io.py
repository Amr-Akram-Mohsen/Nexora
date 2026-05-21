"""
I/O helpers for commercial integrations.

Provides simple utilities to load per-store `raw_html/p{index}.html`
files and to resolve HTML fields for batch entries. Kept minimal — the
parser modules can override or extend this behaviour if needed.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger("commercial.io")


def load_html_for_product(store_slug: str, index: int) -> Dict[str, str]:
    """Load `p{index}.html` from the store package `raw_html` directory.

    Returns a dict suitable for `raw.update(...)` (e.g. `{"html": "..."}`).
    If the file is missing an empty `"html"` string is returned.
    """
    html_path = Path(__file__).parent / store_slug / "raw_html" / f"p{index}.html"
    if not html_path.exists():
        logger.debug("[IO] Missing HTML file: %s", html_path)
        return {"html": ""}
    try:
        return {"html": html_path.read_text(encoding="utf-8")}
    except Exception:
        logger.exception("[IO] Failed to read HTML file: %s", html_path)
        return {"html": ""}


def resolve_html_fields(raw: dict, batch_dir: Path) -> dict:
    """Resolve any fields in `raw` that look like a relative HTML filename.

    If a field value ends with `.html` and does not contain angle brackets
    we try to read it from `batch_dir` and substitute the file content.
    """
    result = dict(raw)
    for k, v in raw.items():
        if not isinstance(v, str):
            continue
        stripped = v.strip()
        if not stripped.endswith(".html") or "<" in stripped:
            continue
        candidate = (batch_dir / stripped).resolve()
        if candidate.exists():
            try:
                result[k] = candidate.read_text(encoding="utf-8")
            except Exception:
                logger.exception("[IO] Failed to read batch HTML file: %s", candidate)
                result[k] = ""
        else:
            logger.debug("[IO] Batch HTML file not found: %s (field=%s)", candidate, k)
            result[k] = ""
    return result
