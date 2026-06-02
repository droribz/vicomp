"""מצב פנימי בין הרצות — לזיהוי 'חדש מאז הרצה קודמת'."""
from __future__ import annotations

import json
from pathlib import Path


class State:
    """עוטף את _state.json. שומר אילו מפתחות-זיהוי כבר נראו."""

    def __init__(self, path: Path):
        self.path = path
        self._seen: set[str] = set()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._seen = set(data.get("seen_keys", []))
            except (json.JSONDecodeError, OSError):
                self._seen = set()

    def is_new(self, identity_key: str) -> bool:
        """האם המכרז לא נראה בהרצה קודמת."""
        return identity_key not in self._seen

    def mark_seen(self, identity_key: str) -> None:
        self._seen.add(identity_key)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"seen_keys": sorted(self._seen)},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
