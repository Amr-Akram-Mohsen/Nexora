import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_CACHE = Path("instance") / "cache"


class RotationState:
    """
    Manages persistent cursors for round-robin rotation of items (e.g. brands).
    Stored in instance/cache/<namespace>_rotation.json.

    Safe to instantiate outside a Flask request context — falls back to a
    relative path if the Flask app context is not available.
    """

    def __init__(self, namespace: str):
        self.namespace = namespace
        try:
            from flask import current_app

            self.cache_dir = Path(current_app.instance_path) / "cache"
        except RuntimeError:
            self.cache_dir = _DEFAULT_CACHE
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.cache_dir / f"{namespace}_rotation.json"
        self.state = self._load()

    def _load(self) -> dict:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def get_next(self, key: str, items: list):
        """
        Returns the next item from the list in a round-robin fashion.
        """
        if not items:
            return None

        current_idx = self.state.get(key, 0)

        # Ensure index is within bounds
        if current_idx >= len(items):
            current_idx = 0

        selected_item = items[current_idx]

        # Advance index for next time
        self.state[key] = (current_idx + 1) % len(items)
        self._save()

        return selected_item

    def peek(self, key: str, items: list):
        """Returns the current item without advancing."""
        if not items:
            return None
        current_idx = self.state.get(key, 0)
        if current_idx >= len(items):
            current_idx = 0
        return items[current_idx]
