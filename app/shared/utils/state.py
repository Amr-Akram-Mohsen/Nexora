"""
Unified JSON-backed state and cursor persistence for background tasks and scrapers.

Persists lightweight cursor states under instance/cache/ so fetchers and rotations
survive process restarts and pick up where they left off.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path("instance") / "cache"


def get_state_dir(subfolder: str = "") -> Path:
    """Return the base directory for state persistence, ensuring it exists."""
    try:
        from flask import current_app
        base = Path(current_app.instance_path) / "cache"
    except RuntimeError:
        base = _DEFAULT_CACHE_DIR

    if subfolder:
        base = base / subfolder

    base.mkdir(parents=True, exist_ok=True)
    return base


class JsonStateStore:
    """Generic atomic JSON file persistence."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.state: dict = self._load()

    def _load(self) -> dict:
        if self.file_path.exists():
            try:
                with self.file_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("[STATE] File %s corrupt or unreadable (%s) — resetting", self.file_path.name, exc)
        return {}

    def save(self) -> None:
        try:
            with self.file_path.open("w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except OSError as exc:
            logger.warning("[STATE] Failed to save %s (%s)", self.file_path.name, exc)


class BatchState:
    """Tracks which taxonomy parent group (e.g. 'technology', 'perfumes') to process."""

    def __init__(self, source: str) -> None:
        self.source = source
        state_dir = get_state_dir("batch_state")
        self._store = JsonStateStore(state_dir / f"{source}_batch.json")
        if "cursor" not in self._store.state:
            self._store.state["cursor"] = 0

    def current_group(self, groups: List[str]) -> Optional[str]:
        if not groups:
            return None
        idx = self._store.state.get("cursor", 0) % len(groups)
        return groups[idx]

    def advance(self, groups: List[str]) -> None:
        if not groups:
            return
        current_idx = self._store.state.get("cursor", 0)
        self._store.state["cursor"] = (current_idx + 1) % len(groups)
        self._store.save()
        try:
            from app.shared.utils.logging import log_batch_rotation
            log_batch_rotation(logger, self.source, next_group=groups[self._store.state["cursor"]])
        except Exception:
            pass

    def reset(self) -> None:
        self._store.state["cursor"] = 0
        self._store.save()

    @property
    def cursor(self) -> int:
        return self._store.state.get("cursor", 0)


class QueryCursorState:
    """Tracks per-(source, section, category) query offsets across fetch runs."""

    def __init__(self, source: str) -> None:
        self.source = source
        state_dir = get_state_dir("query_cursor_state")
        self._store = JsonStateStore(state_dir / f"{source}.json")
        self.state = self._store.state

    def get(self, section: str, category: str) -> int:
        return self.state.get(section, {}).get(category, 0)

    def update(self, section: str, category: str, executed_index: int, total: int) -> None:
        next_index = (executed_index + 1) % total if total > 0 else 0
        self.state.setdefault(section, {})[category] = next_index

    def commit(self) -> None:
        self._store.save()


class RotationState:
    """Manages round-robin rotation of items (e.g. brand lists)."""

    def __init__(self, namespace: str) -> None:
        self.namespace = namespace
        state_dir = get_state_dir()
        self._store = JsonStateStore(state_dir / f"{namespace}_rotation.json")
        self.state = self._store.state

    def get_next(self, key: str, products: list) -> Any:
        if not products:
            return None
        current_idx = self.state.get(key, 0)
        if current_idx >= len(products):
            current_idx = 0
        selected_item = products[current_idx]
        self.state[key] = (current_idx + 1) % len(products)
        self._store.save()
        return selected_item

    def peek(self, key: str, products: list) -> Any:
        if not products:
            return None
        current_idx = self.state.get(key, 0)
        if current_idx >= len(products):
            current_idx = 0
        return products[current_idx]
