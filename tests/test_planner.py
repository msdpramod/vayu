import pytest
from fastapi.testclient import TestClient

from app.actions import ActionExecutorRegistry, PENDING, ProposedActionStore, actions
from app.main import app
from app.planner import (
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


def test_local_planner_requires_explicit_allowlisted_proposal_syntax(tmp_path):
    store = ProposedActionStore(str(tmp_path / "planner.db"))
    service = PlannerService(store)

    no_action = service.plan("send an email someday")
    assert no_action["proposed_action"] is None

    proposed = service.plan("propose email.send: Send the reviewed launch update")
    assert proposed["proposed_action"]["status"] == PENDING
    assert proposed["proposed_action"]["risk"] == "confirm"


def test_plan_api_creates_pending_proposal_only():
    client = TestClient(app)
    actions.clear()
    try:
        response = client.post(
            "/plan",
            json={"prompt": "propose notification.send: Notify me after review"},
        )
        assert response.status_code == 200
        body = response.json()
        action = body["proposed_action"]
        assert action["status"] == PENDING
        assert action["tool"] == "notification.send"

        execute = client.post(f"/actions/{action['id']}/execute")
        assert execute.status_code == 409
    finally:
        actions.clear()
