from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from threading import Lock


class ReminderStore:
    """Durable reminder queue backed by SQLite.

    Vayu stores due times in UTC. Delivery is intentionally separate from storage:
    callers can poll ``due()`` or the API's ``/reminders/due`` endpoint and route
    notifications through an explicit notifier skill later.
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
                """CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    dismissed_at TEXT
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminders_status_due_at ON reminders(status, due_at)"
            )

    @staticmethod
    def parse_due_at(value: str) -> datetime:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("Use an ISO-8601 timestamp, for example 2026-08-13T10:30:00Z.") from exc
        if parsed.tzinfo is None:
            raise ValueError("Reminder timestamps must include a timezone offset or Z.")
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _utc_text(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def add(self, message: str, due_at: str) -> dict[str, object]:
        message = message.strip()
        if not message:
            raise ValueError("Reminder message cannot be empty.")
        due = self.parse_due_at(due_at)
        due_text = self._utc_text(due)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO reminders(message, due_at) VALUES (?, ?)",
                (message, due_text),
            )
            row = connection.execute(
                "SELECT id, message, due_at, status, created_at, dismissed_at FROM reminders WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return dict(row)

    def list(self, include_dismissed: bool = False, limit: int = 50) -> list[dict[str, object]]:
        safe_limit = max(1, min(limit, 200))
        query = "SELECT id, message, due_at, status, created_at, dismissed_at FROM reminders"
        params: tuple[object, ...]
        if include_dismissed:
            query += " ORDER BY due_at ASC, id ASC LIMIT ?"
            params = (safe_limit,)
        else:
            query += " WHERE status = 'open' ORDER BY due_at ASC, id ASC LIMIT ?"
            params = (safe_limit,)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def due(self, now: datetime | None = None, limit: int = 50) -> list[dict[str, object]]:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        now_text = self._utc_text(current)
        safe_limit = max(1, min(limit, 200))
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT id, message, due_at, status, created_at, dismissed_at
                   FROM reminders
                   WHERE status = 'open' AND due_at <= ?
                   ORDER BY due_at ASC, id ASC LIMIT ?""",
                (now_text, safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def dismiss(self, reminder_id: int) -> dict[str, object] | None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE reminders
                   SET status = 'dismissed', dismissed_at = CURRENT_TIMESTAMP
                   WHERE id = ? AND status = 'open'""",
                (reminder_id,),
            )
            row = connection.execute(
                "SELECT id, message, due_at, status, created_at, dismissed_at FROM reminders WHERE id = ?",
                (reminder_id,),
            ).fetchone()
        return dict(row) if row else None

    def clear(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM reminders")


reminders = ReminderStore()
