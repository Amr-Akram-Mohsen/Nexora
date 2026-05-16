import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_DIR = Path("instance") / "cache" / "query_cursor_state"


def _state_dir() -> Path:
    """Return the directory used for query cursor files, creating it if needed.

    Mirrors BatchState: prefer Flask instance path so all persistent state lands
    in the same location regardless of the CWD when the process starts.
    """
    try:
        from flask import current_app

        base = Path(current_app.instance_path) / "cache" / "query_cursor_state"
    except RuntimeError:
        base = _DEFAULT_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base


class QueryCursorState:
    """
    Tracks per-(source, section, category) query offsets so each fetch run
    begins where the previous one left off, cycling through the full query list.

    The stored value for a key is the index of the **next** query to execute,
    not the last query that was executed.  This ensures the first query on the
    next run is always a fresh one.
    """

    def __init__(self, source: str) -> None:
        self.source = source
        self.file = _state_dir() / f"{source}.json"
        self.state: dict = self._load()
        self._totals: dict = {}  # keyed by (section, category)

    def _load(self) -> dict:
        if self.file.exists():
            try:
                with self.file.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "[CURSOR][%s] state file corrupt — resetting  err=%s",
                    self.source,
                    exc,
                )
        return {}

    def _save(self) -> None:
        try:
            with self.file.open("w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except OSError as exc:
            logger.warning(
                "[CURSOR][%s] could not save state  err=%s", self.source, exc
            )

    def get(self, section: str, category: str) -> int:
        """Return the next-to-execute query index for this section/category."""
        return self.state.get(section, {}).get(category, 0)

    def update(self, section: str, category: str, executed_index: int, total: int) -> None:
        """
        Advance the cursor to the query AFTER the one just executed.

        Args:
            executed_index: The flat index (0-based) of the query that was just run.
            total: Total number of queries for this section/category combination.
        """
        next_index = (executed_index + 1) % total if total > 0 else 0
        self.state.setdefault(section, {})[category] = next_index

    def commit(self) -> None:
        self._save()