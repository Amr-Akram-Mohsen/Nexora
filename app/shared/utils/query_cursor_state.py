import json
from pathlib import Path


class QueryCursorState:
    def __init__(self, source: str):
        self.path = Path("instance/cache/query_cursor_state")
        self.path.mkdir(parents=True, exist_ok=True)

        self.file = self.path / f"{source}.json"

        self.state = self._load()

    def _load(self):
        if self.file.exists():
            return json.load(open(self.file, "r"))
        return {}

    def _save(self):
        with open(self.file, "w") as f:
            json.dump(self.state, f, indent=2)

    def get(self, section: str, category: str) -> int:
        return self.state.get(section, {}).get(category, 0)

    def update(self, section: str, category: str, index: int):
        self.state.setdefault(section, {})[category] = index

    def commit(self):
        self._save()