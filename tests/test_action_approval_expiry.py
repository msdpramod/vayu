from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from app.actions import (
    ActionExecutorRegistry,
    EXECUTED,
    EXPIRED,
    ProposedActionStore,
)


def _age_approval(store: ProposedActionStore, action_id: int, seconds: int) -> None:
    approved_at = (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()
    with store._connect() as connection:
        connection.execute(
            "UPDATE proposed_actions SET approved_at = ? WHERE id = ?",
            (approved_at, action_id),
        )


def test_stale_approval_expires_before_executor_is_called(tmp_path):
    store = ProposedActionStore(str(tmp_path / "actions.db"), approval_ttl_seconds=60)
    registry = ActionExecutorRegistry(store)
    calls = []
    registry.register("test.echo", lambda payload: calls.append(payload))

    action = store.propose("test.echo", "Must not execute after approval expires")
    store.approve(action["id"])
    _age_approval(store, action["id"], seconds=61)

    with pytest.raises(PermissionError):
        registry.execute(action["id"])

    expired = store.get(action["id"])
    assert expired["status"] == EXPIRED
    assert expired["expired_at"] is not None
    assert calls == []
    assert store.events(action["id"])[-1]["event"] == EXPIRED


def test_fresh_approval_still_executes_normally(tmp_path):
    store = ProposedActionStore(str(tmp_path / "actions.db"), approval_ttl_seconds=60)
    registry = ActionExecutorRegistry(store)
    registry.register("test.echo", lambda payload: {"echo": payload["message"]})

    action = store.propose(
        "test.echo",
        "Execute while approval is fresh",
        {"message": "hello"},
    )
    store.approve(action["id"])

    result = registry.execute(action["id"])

    assert result["action"]["status"] == EXECUTED
    assert result["result"] == {"echo": "hello"}


def test_existing_database_is_migrated_with_expired_at_column(tmp_path):
    db_path = tmp_path / "actions.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE proposed_actions (
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
            )
            """
        )

    migrated = ProposedActionStore(str(db_path))
    with migrated._connect() as connection:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(proposed_actions)").fetchall()
        }

    assert "expired_at" in columns
