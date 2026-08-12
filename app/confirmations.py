from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import secrets
import sqlite3
from threading import Lock


class ConfirmationStore:
    """Issues short-lived, one-time confirmation tokens bound to exact commands."""

    def __init__(self, db_path: str | None = None, ttl_seconds: int = 300):
        self.db_path = Path(db_path or os.getenv("VAYU_DB_PATH", "data/vayu.db"))
        self.ttl_seconds = ttl_seconds
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
                """CREATE TABLE IF NOT EXISTS confirmation_challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_hash TEXT NOT NULL UNIQUE,
                    command TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    consumed_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def issue(self, command: str) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds)
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO confirmation_challenges(token_hash, command, expires_at) VALUES (?, ?, ?)",
                (self._hash(token), command, expires_at.isoformat()),
            )
            connection.execute(
                "DELETE FROM confirmation_challenges WHERE expires_at < ? OR consumed_at IS NOT NULL",
                ((datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),),
            )
        return token

    def consume(self, token: str, command: str) -> bool:
        token_hash = self._hash(token)
        now = datetime.now(timezone.utc)
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT command, expires_at, consumed_at FROM confirmation_challenges WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
            if row is None or row["consumed_at"] is not None or row["command"] != command:
                return False
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at <= now:
                return False
            connection.execute(
                "UPDATE confirmation_challenges SET consumed_at = ? WHERE token_hash = ? AND consumed_at IS NULL",
                (now.isoformat(), token_hash),
            )
        return True

    def clear(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM confirmation_challenges")


confirmations = ConfirmationStore()
