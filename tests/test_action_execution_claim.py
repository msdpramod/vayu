from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from app.actions import (
    ActionExecutorRegistry,
    APPROVED,
    EXECUTED,
    EXECUTION_FAILED,
    EXECUTING,
    ProposedActionStore,
)


def test_only_one_worker_can_claim_and_execute_an_approved_action(tmp_path):
    store = ProposedActionStore(str(tmp_path / "actions.db"))
    registry = ActionExecutorRegistry(store)
    entered = Event()
    release = Event()
    calls = []

    def executor(payload):
        calls.append(payload)
        entered.set()
        assert release.wait(timeout=2)
        return {"ok": True}

    registry.register("test.echo", executor)
    action = store.propose("test.echo", "Execute exactly once", {"message": "hello"})
    store.approve(action["id"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(registry.execute, action["id"])
        assert entered.wait(timeout=1)
        assert store.get(action["id"])["status"] == EXECUTING

        second = pool.submit(registry.execute, action["id"])
        with pytest.raises(PermissionError):
            second.result(timeout=1)

        release.set()
        result = first.result(timeout=2)

    assert result["action"]["status"] == EXECUTED
    assert calls == [{"message": "hello"}]
    assert [event["event"] for event in store.events(action["id"])] == [
        "proposed",
        "approved",
        "executing",
        "executed",
    ]


def test_executor_failure_is_terminal_and_not_implicitly_retried(tmp_path):
    store = ProposedActionStore(str(tmp_path / "actions.db"))
    registry = ActionExecutorRegistry(store)
    calls = []

    def failing_executor(payload):
        calls.append(payload)
        raise RuntimeError("downstream failed after dispatch may have started")

    registry.register("test.echo", failing_executor)
    action = store.propose("test.echo", "Do not retry ambiguous side effect", {"message": "hello"})
    store.approve(action["id"])

    with pytest.raises(RuntimeError):
        registry.execute(action["id"])

    failed = store.get(action["id"])
    assert failed["status"] == EXECUTION_FAILED
    assert calls == [{"message": "hello"}]
    last_event = store.events(action["id"])[-1]
    assert last_event["event"] == EXECUTION_FAILED
    assert last_event["detail"] == "RuntimeError"

    with pytest.raises(PermissionError):
        registry.execute(action["id"])
    assert calls == [{"message": "hello"}]


def test_claim_execution_is_atomic_at_store_boundary(tmp_path):
    store = ProposedActionStore(str(tmp_path / "actions.db"))
    action = store.propose("test.echo", "Claim once")
    store.approve(action["id"])

    claimed = store.claim_execution(action["id"])
    assert claimed["status"] == EXECUTING

    with pytest.raises(ValueError):
        store.claim_execution(action["id"])
