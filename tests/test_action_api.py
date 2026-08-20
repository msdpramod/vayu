from fastapi.testclient import TestClient

import app.main as main
from app.actions import ActionExecutorRegistry, ProposedActionStore


client = TestClient(main.app)


def test_action_api_fails_closed_until_approved_and_adapter_exists(tmp_path, monkeypatch):
    store = ProposedActionStore(str(tmp_path / "actions.db"))
    registry = ActionExecutorRegistry(store)
    monkeypatch.setattr(main, "actions", store)
    monkeypatch.setattr(main, "executors", registry)

    proposed = client.post(
        "/actions",
        json={
            "tool": "email.send",
            "description": "Send a reviewed email",
            "payload": {"to": "owner@example.com", "subject": "Vayu"},
        },
    )
    assert proposed.status_code == 201
    action_id = proposed.json()["id"]
    assert proposed.json()["status"] == "pending_approval"

    blocked = client.post(f"/actions/{action_id}/execute")
    assert blocked.status_code == 409

    approved = client.post(f"/actions/{action_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    missing_adapter = client.post(f"/actions/{action_id}/execute")
    assert missing_adapter.status_code == 501
    assert store.get(action_id)["status"] == "approved"

    registry.register("email.send", lambda payload: {"delivery": "simulated", "to": payload["to"]})
    executed = client.post(f"/actions/{action_id}/execute")
    assert executed.status_code == 200
    assert executed.json()["action"]["status"] == "executed"
    assert executed.json()["result"]["delivery"] == "simulated"

    events = client.get(f"/actions/{action_id}/events")
    assert [event["event"] for event in events.json()["events"]] == [
        "proposed",
        "approved",
        "executing",
        "executed",
    ]


def test_action_api_rejection_is_terminal(tmp_path, monkeypatch):
    store = ProposedActionStore(str(tmp_path / "actions.db"))
    registry = ActionExecutorRegistry(store)
    monkeypatch.setattr(main, "actions", store)
    monkeypatch.setattr(main, "executors", registry)

    proposed = client.post(
        "/actions",
        json={"tool": "calendar.create", "description": "Create a calendar event"},
    )
    action_id = proposed.json()["id"]

    rejected = client.post(f"/actions/{action_id}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    assert client.post(f"/actions/{action_id}/approve").status_code == 409
    assert client.post(f"/actions/{action_id}/execute").status_code == 409
