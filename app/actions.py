from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Any


PENDING = "pending_approval"
APPROVED = "approved"
REJECTED = "rejected"
EXECUTED = "executed"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProposedActionStore:
    """Durable human-in-the-loop action lifecycle backed by SQLite."""

    def __init__(self, db_path: str | None = None):
        self.db_path = Path(db_path or os.getenv("VAYU_DB_PATH", "data/vayu.db"))
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS proposed_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool TEXT NOT NULL,
                    description TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    approved_at TEXT,
                    rejected_at TEXT,
                    executed_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_proposed_actions_status
                    ON proposed_actions(status, id DESC);

                CREATE TABLE IF NOT EXISTS action_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id INTEGER NOT NULL,
                    event TEXT NOT NULL,
                    detail TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(action_id) REFERENCES proposed_actions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_action_events_action
                    ON action_events(action_id, id);
                """
            )

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        return item

    def _event(
        self,
        connection: sqlite3.Connection,
        action_id: int,
        event: str,
        detail: str | None = None,
    ) -> None:
        connection.execute(
            "INSERT INTO action_events(action_id, event, detail, created_at) VALUES (?, ?, ?, ?)",
            (action_id, event, detail, _utc_now()),
        )

    def propose(
        self,
        tool: str,
        description: str,
        payload: dict[str, Any] | None = None,
        risk: str = "confirm",
    ) -> dict[str, Any]:
        if risk not in {"safe", "confirm"}:
            raise ValueError("Action risk must be 'safe' or 'confirm'.")
        tool = tool.strip()
        description = description.strip()
        if not tool or not description:
            raise ValueError("Tool and description are required.")

        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO proposed_actions(
                    tool, description, payload_json, risk, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tool,
                    description,
                    json.dumps(payload or {}, sort_keys=True, separators=(",", ":")),
                    risk,
                    PENDING,
                    _utc_now(),
                ),
            )
            action_id = int(cursor.lastrowid)
            self._event(connection, action_id, "proposed")
        return self.get(action_id)

    def get(self, action_id: int) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM proposed_actions WHERE id = ?",
                (action_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Action {action_id} was not found.")
        return self._decode(row)

    def list(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 200))
        with self._connect() as connection:
            if status:
                rows = connection.execute(
                    "SELECT * FROM proposed_actions WHERE status = ? ORDER BY id DESC LIMIT ?",
                    (status, safe_limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM proposed_actions ORDER BY id DESC LIMIT ?",
                    (safe_limit,),
                ).fetchall()
        return [self._decode(row) for row in rows]

    def events(self, action_id: int, limit: int = 100) -> list[dict[str, Any]]:
        self.get(action_id)
        safe_limit = max(1, min(limit, 500))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, action_id, event, detail, created_at
                FROM action_events
                WHERE action_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (action_id, safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def _transition(self, action_id: int, target: str, timestamp_column: str) -> dict[str, Any]:
        if target not in {APPROVED, REJECTED, EXECUTED}:
            raise ValueError("Unsupported action transition.")

        expected = APPROVED if target == EXECUTED else PENDING
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                f"""
                UPDATE proposed_actions
                SET status = ?, {timestamp_column} = ?
                WHERE id = ? AND status = ?
                """,
                (target, _utc_now(), action_id, expected),
            )
            if cursor.rowcount != 1:
                row = connection.execute(
                    "SELECT status FROM proposed_actions WHERE id = ?",
                    (action_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(f"Action {action_id} was not found.")
                raise ValueError(
                    f"Action {action_id} cannot transition from {row['status']} to {target}."
                )
            self._event(connection, action_id, target)
        return self.get(action_id)

    def approve(self, action_id: int) -> dict[str, Any]:
        return self._transition(action_id, APPROVED, "approved_at")

    def reject(self, action_id: int) -> dict[str, Any]:
        return self._transition(action_id, REJECTED, "rejected_at")

    def mark_executed(self, action_id: int) -> dict[str, Any]:
        return self._transition(action_id, EXECUTED, "executed_at")

    def record_execution_failure(self, action_id: int, detail: str) -> None:
        with self._lock, self._connect() as connection:
            self._event(connection, action_id, "execution_failed", detail[:500])

    def clear(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM action_events")
            connection.execute("DELETE FROM proposed_actions")


Executor = Callable[[dict[str, Any]], Any]


class ActionExecutorRegistry:
    """Allow-listed tool adapters. Approval is mandatory before any adapter is invoked."""

    def __init__(self, store: ProposedActionStore):
        self.store = store
        self._executors: dict[str, Executor] = {}

    def register(self, tool: str, executor: Executor) -> None:
        tool = tool.strip()
        if not tool:
            raise ValueError("Tool name is required.")
        self._executors[tool] = executor

    def registered_tools(self) -> list[str]:
        return sorted(self._executors)

    def execute(self, action_id: int) -> dict[str, Any]:
        action = self.store.get(action_id)
        if action["status"] != APPROVED:
            raise PermissionError(
                f"Action {action_id} must be explicitly approved before execution."
            )

        executor = self._executors.get(action["tool"])
        if executor is None:
            raise LookupError(
                f"No allow-listed executor is installed for tool '{action['tool']}'."
            )

        try:
            result = executor(action["payload"])
        except Exception as exc:
            self.store.record_execution_failure(action_id, type(exc).__name__)
            raise

        updated = self.store.mark_executed(action_id)
        return {"action": updated, "result": result}


actions = ProposedActionStore()
executors = ActionExecutorRegistry(actions)
