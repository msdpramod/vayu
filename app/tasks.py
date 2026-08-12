from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from threading import Lock


class TaskStore:
    """Durable local task list backed by SQLite."""

    def __init__(self, db_path: str | None = None):
        self.db_path = Path(db_path or os.getenv("VAYU_DB_PATH", "data/vayu.db"))
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
                """CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT
                )"""
            )

    def add(self, title: str) -> dict[str, object]:
        title = title.strip()
        if not title:
            raise ValueError("Task title cannot be empty.")
        with self._lock, self._connect() as connection:
            cursor = connection.execute("INSERT INTO tasks(title) VALUES (?)", (title,))
            task_id = cursor.lastrowid
            row = connection.execute(
                "SELECT id, title, status, created_at, completed_at FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        return dict(row)

    def list(self, include_completed: bool = False, limit: int = 50) -> list[dict[str, object]]:
        safe_limit = max(1, min(limit, 200))
        query = "SELECT id, title, status, created_at, completed_at FROM tasks"
        params: tuple[object, ...]
        if include_completed:
            query += " ORDER BY id DESC LIMIT ?"
            params = (safe_limit,)
        else:
            query += " WHERE status = 'open' ORDER BY id DESC LIMIT ?"
            params = (safe_limit,)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def complete(self, task_id: int) -> dict[str, object] | None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE tasks
                   SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                   WHERE id = ? AND status = 'open'""",
                (task_id,),
            )
            row = connection.execute(
                "SELECT id, title, status, created_at, completed_at FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        return dict(row) if row else None

    def clear(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM tasks")


tasks = TaskStore()
