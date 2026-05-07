# app/shared/utils/batch_state.py
"""
Lightweight taxonomy-group batch cursor.

Persists a small JSON file under the instance/cache directory so each
fetch run can pick up from where the previous one left off, rotating
through the taxonomy parent groups (electronics → perfumes → accessories)
instead of always starting from the beginning.

No external dependencies — plain stdlib json + pathlib.

Usage::

    state = BatchState("newsapi")
    group   = state.current_group(GROUPS)   # e.g. "electronics"
    state.advance(GROUPS)                   # move cursor to next group
"""
import json
import logging
import os
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Default storage directory — falls back to cwd/instance/cache if Flask
# app context is not available.
_DEFAULT_DIR = Path("instance") / "cache" / "batch_state"


def _state_dir() -> Path:
    """Return the directory used for batch state files, creating it if needed."""
    try:
        from flask import current_app
        base = Path(current_app.instance_path) / "cache" / "batch_state"
    except RuntimeError:
        base = _DEFAULT_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base


def _state_path(source: str) -> Path:
    return _state_dir() / f"{source}_batch.json"


class BatchState:
    """
    Tracks which taxonomy parent group (e.g. 'electronics', 'perfumes',
    'accessories') should be processed in the current fetch run.

    The cursor value is the *index* into ``groups`` and is stored on disk
    so it survives across process restarts.

    Args:
        source: Identifier for the fetch source (e.g. 'newsapi', 'youtube').
    """

    def __init__(self, source: str) -> None:
        self.source = source
        self._path = _state_path(source)
        self._data: dict = self._load()

    # ── persistence ───────────────────────────────────────────────────

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with self._path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "[BATCH][%s] state file corrupt or unreadable — resetting  err=%s",
                    self.source, exc,
                )
        return {"cursor": 0}

    def _save(self) -> None:
        try:
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(self._data, f)
        except OSError as exc:
            logger.warning("[BATCH][%s] could not save state  err=%s", self.source, exc)

    # ── public API ────────────────────────────────────────────────────

    def current_group(self, groups: List[str]) -> Optional[str]:
        """Return the group name that should be processed this run."""
        if not groups:
            return None
        idx = self._data.get("cursor", 0) % len(groups)
        return groups[idx]

    def advance(self, groups: List[str]) -> None:
        """Move cursor to the next group and persist."""
        if not groups:
            return
        current_idx = self._data.get("cursor", 0)
        self._data["cursor"] = (current_idx + 1) % len(groups)
        self._save()
        next_group = groups[self._data["cursor"]]
        logger.info(
            "[BATCH][%s] cursor advanced  next_group=%s",
            self.source, next_group,
        )

    def reset(self) -> None:
        """Reset cursor to 0 (useful in tests or manual overrides)."""
        self._data = {"cursor": 0}
        self._save()

    @property
    def cursor(self) -> int:
        return self._data.get("cursor", 0)
