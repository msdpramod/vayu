from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from threading import Lock

from app.reminders import ReminderStore, reminders


class NotificationOutbox:
    """Durable local notification outbox.

    This is intentionally not an OS/email/push sender. It converts due reminders
    into idempotent delivery records that a future explicit adapter can consume.
    """

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
                """CREATE TABLE IF NOT EXISTS notification_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reminder_id INTEGER NOT NULL UNIQUE,
                    channel TEXT NOT NULL DEFAULT 'local',
                    message TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_notification_outbox_status ON notification_outbox(status, id)"
            )

    def enqueue_due(self, reminder_store: ReminderStore | None = None, limit: int = 50) -> list[dict[str, object]]:
        store = reminder_store or reminders
        due = store.due(limit=limit)
        if not due:
            return []
        created_ids: list[int] = []
        with self._lock, self._connect() as connection:
            for reminder in due:
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO notification_outbox(reminder_id, message, due_at)
                       VALUES (?, ?, ?)""",
                    (reminder["id"], reminder["message"], reminder["due_at"]),
                )
                if cursor.rowcount:
                    created_ids.append(int(cursor.lastrowid))
            if not created_ids:
                return []
            placeholders = ",".join("?" for _ in created_ids)
            rows = connection.execute(
                f"SELECT id, reminder_id, channel, message, due_at, status, created_at FROM notification_outbox WHERE id IN ({placeholders}) ORDER BY id",
                tuple(created_ids),
            ).fetchall()
        return [dict(row) for row in rows]

    def list(self, status: str = "pending", limit: int = 50) -> list[dict[str, object]]:
        if status not in {"pending"}:
            raise ValueError("Unsupported notification status.")
        safe_limit = max(1, min(limit, 200))
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT id, reminder_id, channel, message, due_at, status, created_at
                   FROM notification_outbox WHERE status = ? ORDER BY id LIMIT ?""",
                (status, safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def clear(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM notification_outbox")


notifications = NotificationOutbox()
