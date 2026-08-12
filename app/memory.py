from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from threading import Lock


class ConversationMemory:
    """Durable bounded memory backed by SQLite."""

    def __init__(self, db_path: str | None = None, max_items: int = 200):
        self.db_path = Path(db_path or os.getenv("VAYU_DB_PATH", "data/vayu.db"))
        self.max_items = max_items
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )

    def add(self, role: str, content: str) -> None:
        content = content.strip()
        if not content:
            return
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO memories(role, content) VALUES (?, ?)",
                (role, content),
            )
            connection.execute(
                """DELETE FROM memories WHERE id NOT IN (
                    SELECT id FROM memories ORDER BY id DESC LIMIT ?
                )""",
                (self.max_items,),
            )

    def recent(self, limit: int = 10) -> list[dict[str, str]]:
        safe_limit = max(1, min(limit, self.max_items))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT role, content, created_at FROM memories ORDER BY id DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def clear(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM memories")


memory = ConversationMemory()
