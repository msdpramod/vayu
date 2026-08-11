from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict
from threading import Lock


@dataclass
class MemoryItem:
    role: str
    content: str


class ConversationMemory:
    def __init__(self, max_items: int = 50):
        self._items: deque[MemoryItem] = deque(maxlen=max_items)
        self._lock = Lock()

    def add(self, role: str, content: str) -> None:
        with self._lock:
            self._items.append(MemoryItem(role=role, content=content))

    def recent(self, limit: int = 10) -> list[dict[str, str]]:
        with self._lock:
            items = list(self._items)[-limit:]
        return [asdict(item) for item in items]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


memory = ConversationMemory()
