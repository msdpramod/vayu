import sqlite3

import pytest

from app.actions import (
    ActionExecutorRegistry,
    APPROVED,
    EXECUTED,
    PENDING,
    REJECTED,
    ProposedActionStore,
)


def test_action_requires_approval_before_executor_is_invoked(tmp_path):
    store = ProposedActionStore(str(tmp_path / "actions.db"))
    registry = ActionExecutorRegistry(store)
    calls = []
    registry.register("test.echo", lambda payload: calls.append(payload) or {"ok": True})

    action = store.propose("test.echo", "Echo a test payload", {"message": "hello"})
    assert action["status"] == PENDING

    with pytest.raises(PermissionError):
        registry.execute(action["id"])
    assert calls == []

    approved = store.approve(action["id"])
    assert approved["status"] == APPROVED

    result = registry.execute(action["id"])
    assert result["action"]["status"] == EXECUTED
    assert result["result"] == {"ok": True}
    assert calls == [{"message": "hello"}]


def test_rejected_action_can_never_execute(tmp_path):
    store = ProposedActionStore(str(tmp_path / "actions.db"))
    registry = ActionExecutorRegistry(store)
    registry.register("test.echo", lambda payload: payload)

    action = store.propose("test.echo", "Rejected action")
    rejected = store.reject(action["id"])
    assert rejected["status"] == REJECTED

    with pytest.raises(PermissionError):
        registry.execute(action["id"])
    with pytest.raises(ValueError):
        store.approve(action["id"])


def test_action_events_are_durable_and_ordered(tmp_path):
    db = tmp_path / "actions.db"
    first = ProposedActionStore(str(db))
    action = first.propose("email.send", "Send a reviewed email", {"to": "user@example.com"})
    first.approve(action["id"])

    second = ProposedActionStore(str(db))
    events = second.events(action["id"])
    assert [event["event"] for event in events] == ["proposed", "approved"]
    assert second.get(action["id"])["status"] == APPROVED


def test_missing_executor_fails_closed_after_approval(tmp_path):
    store = ProposedActionStore(str(tmp_path / "actions.db"))
    registry = ActionExecutorRegistry(store)
    action = store.propose("email.send", "Send email")
    store.approve(action["id"])

    with pytest.raises(LookupError):
        registry.execute(action["id"])

    assert store.get(action["id"])["status"] == APPROVED


def test_direct_action_proposal_uses_shared_payload_policy(tmp_path):
    store = ProposedActionStore(str(tmp_path / "actions.db"))

    with pytest.raises(ValueError):
        store.propose(
            "email.send",
            "Attempt to stage a secret",
            {"recipient": "user@example.com", "token": "must-not-be-stored"},
        )

    assert store.list() == []


def test_execution_revalidates_stored_payload_before_adapter_invocation(tmp_path):
    db = tmp_path / "actions.db"
    store = ProposedActionStore(str(db))
    registry = ActionExecutorRegistry(store)
    calls = []
    registry.register("test.echo", lambda payload: calls.append(payload) or payload)

    action = store.propose("test.echo", "Echo approved payload", {"message": "safe"})
    store.approve(action["id"])

    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE proposed_actions SET payload_json = ? WHERE id = ?",
            ('{"shell":"unexpected"}', action["id"]),
        )

    with pytest.raises(PermissionError):
        registry.execute(action["id"])

    assert calls == []
    assert store.get(action["id"])["status"] == APPROVED
    assert store.events(action["id"])[-1]["event"] == "execution_failed"
    assert store.events(action["id"])[-1]["detail"] == "payload_policy_violation"
