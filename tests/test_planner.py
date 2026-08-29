import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.actions import ActionExecutorRegistry, PENDING, ProposedActionStore, actions
from app.main import app
from app.planner import (
    OllamaPlanner,
    PlannedAction,
    PlannerDecision,
    PlannerProvider,
    PlannerService,
)


class FixedPlanner(PlannerProvider):
    def __init__(self, decision: PlannerDecision):
        self.decision = decision

    def plan(self, prompt: str) -> PlannerDecision:
        return self.decision


def test_planner_stages_allowlisted_action_without_execution(tmp_path):
    store = ProposedActionStore(str(tmp_path / "planner.db"))
    decision = PlannerDecision(
        reply="I prepared an email proposal for review.",
        action=PlannedAction(
            tool="email.send",
            description="Send the reviewed status update",
            payload={"to": "owner@example.com"},
        ),
        provider="test-planner",
    )
    service = PlannerService(store, FixedPlanner(decision))
    registry = ActionExecutorRegistry(store)
    calls = []
    registry.register("email.send", lambda payload: calls.append(payload))

    result = service.plan("send my update")

    assert result["plan_critique"]["disposition"] == "verified"
    assert result["simulation"]["disposition"] == "ready"
    assert result["simulation"]["failure_modes"]
    assert result["proposed_action"]["status"] == PENDING
    assert result["proposed_action"]["tool"] == "email.send"
    with pytest.raises(PermissionError):
        registry.execute(result["proposed_action"]["id"])
    assert calls == []


def test_planner_unknown_tool_fails_closed(tmp_path):
    store = ProposedActionStore(str(tmp_path / "planner.db"))
    decision = PlannerDecision(
        reply="unsafe",
        action=PlannedAction(
            tool="shell.exec",
            description="Run an arbitrary command",
            payload={"command": "rm -rf /"},
        ),
        provider="test-planner",
    )
    service = PlannerService(store, FixedPlanner(decision))

    with pytest.raises(ValueError, match="not allow-listed"):
        service.plan("do something unsafe")
    assert store.list() == []


def test_planner_cannot_downgrade_confirmation_requirement(tmp_path):
    store = ProposedActionStore(str(tmp_path / "planner.db"))
    decision = PlannerDecision(
        reply="unsafe downgrade",
        action=PlannedAction(
            tool="calendar.create",
            description="Create an event",
            payload={},
            risk="safe",
        ),
        provider="test-planner",
    )
    service = PlannerService(store, FixedPlanner(decision))

    with pytest.raises(ValueError, match="must require confirmation"):
        service.plan("create event")
    assert store.list() == []


def test_local_planner_analyzes_but_does_not_stage_incomplete_proposal(tmp_path):
    store = ProposedActionStore(str(tmp_path / "planner.db"))
    service = PlannerService(store)

    no_action = service.plan("send an email someday")
    assert no_action["proposed_action"] is None

    proposed = service.plan("propose email.send: Send the reviewed launch update")
    assert proposed["plan_critique"]["disposition"] == "verified"
    assert proposed["simulation"]["disposition"] == "needs_revision"
    assert "required field 'to' is unresolved" in proposed["simulation"]["findings"]
    assert proposed["proposed_action"] is None
    assert store.list() == []


def test_ollama_planner_parses_strict_json_without_execution(monkeypatch, tmp_path):
    payload = {
        "reply": "I prepared a notification for review.",
        "action": {
            "tool": "notification.send",
            "description": "Notify the owner after review",
            "payload": {"message": "Build completed"},
            "risk": "confirm",
        },
    }

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": json.dumps(payload)}

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: FakeResponse())
    store = ProposedActionStore(str(tmp_path / "ollama.db"))
    service = PlannerService(store, OllamaPlanner("http://127.0.0.1:11434", "llama3.2"))

    result = service.plan("notify me when the build is done")

    assert result["provider"] == "ollama"
    assert result["simulation"]["disposition"] == "ready"
    assert result["proposed_action"]["status"] == PENDING
    assert result["proposed_action"]["tool"] == "notification.send"


def test_ollama_planner_rejects_extra_action_fields(monkeypatch, tmp_path):
    payload = {
        "reply": "unsafe",
        "action": {
            "tool": "email.send",
            "description": "Send email",
            "payload": {},
            "risk": "confirm",
            "execute": True,
        },
    }

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": json.dumps(payload)}

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: FakeResponse())
    store = ProposedActionStore(str(tmp_path / "ollama-invalid.db"))
    service = PlannerService(store, OllamaPlanner("http://127.0.0.1:11434", "llama3.2"))

    with pytest.raises(ValueError, match="unsupported fields"):
        service.plan("send email")
    assert store.list() == []


def test_ollama_transport_failure_creates_no_action(monkeypatch, tmp_path):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "post", fail)
    store = ProposedActionStore(str(tmp_path / "ollama-offline.db"))
    service = PlannerService(store, OllamaPlanner("http://127.0.0.1:11434", "llama3.2"))

    with pytest.raises(RuntimeError, match="unavailable or invalid"):
        service.plan("send email")
    assert store.list() == []


def test_plan_api_returns_simulation_and_does_not_stage_incomplete_local_proposal():
    client = TestClient(app)
    actions.clear()
    try:
        response = client.post(
            "/plan",
            json={"prompt": "propose notification.send: Notify me after review"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["plan_critique"]["disposition"] == "verified"
        assert body["simulation"]["disposition"] == "needs_revision"
        assert body["proposed_action"] is None
        assert actions.list() == []
    finally:
        actions.clear()
