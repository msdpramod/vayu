from __future__ import annotations

import os
from pathlib import Path
import re
import sqlite3
from threading import Lock


_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(token\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(password\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(secret\s*[:=]\s*)\S+"),
]


def redact_command(command: str) -> str:
    redacted = command
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted[:500]


class AuditStore:
    """Durable audit log for command decisions and execution outcomes."""

    def __init__(self, db_path: str | None = None, max_events: int = 1000):
        self.db_path = Path(db_path or os.getenv("VAYU_DB_PATH", "data/vayu.db"))
        self.max_events = max_events
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
                """CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    status TEXT NOT NULL,
                    executed INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )

    def record(self, command: str, risk: str, intent: str, status: str, executed: bool) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO audit_events(command, risk, intent, status, executed) VALUES (?, ?, ?, ?, ?)",
                (redact_command(command), risk, intent, status, int(executed)),
            )
            connection.execute(
                """DELETE FROM audit_events WHERE id NOT IN (
                    SELECT id FROM audit_events ORDER BY id DESC LIMIT ?
                )""",
                (self.max_events,),
            )

    def recent(self, limit: int = 50) -> list[dict[str, object]]:
        safe_limit = max(1, min(limit, self.max_events))
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT command, risk, intent, status, executed, created_at
                   FROM audit_events ORDER BY id DESC LIMIT ?""",
                (safe_limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["executed"] = bool(item["executed"])
            result.append(item)
        return result

    def clear(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM audit_events")


audit = AuditStore()
