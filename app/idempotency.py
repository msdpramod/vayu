from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
from threading import Lock


class IdempotencyStore:
    """Durably caches command responses by caller-supplied request id."""

    def __init__(self, db_path: str | None = None, max_items: int = 2000):
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
                """CREATE TABLE IF NOT EXISTS idempotency_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL UNIQUE,
                    command TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )

    def get(self, request_id: str, command: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT command, response_json FROM idempotency_results WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        if row["command"] != command:
            raise ValueError("request_id was already used for a different command")
        return json.loads(row["response_json"])

    def put(self, request_id: str, command: str, response: dict) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO idempotency_results(request_id, command, response_json) VALUES (?, ?, ?)",
                (request_id, command, json.dumps(response)),
            )
            connection.execute(
                """DELETE FROM idempotency_results WHERE id NOT IN (
                    SELECT id FROM idempotency_results ORDER BY id DESC LIMIT ?
                )""",
                (self.max_items,),
            )

    def clear(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM idempotency_results")


idempotency = IdempotencyStore()
