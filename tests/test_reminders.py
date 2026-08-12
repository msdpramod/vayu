from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.reminders import ReminderStore, reminders

client = TestClient(app)


def setup_function():
    reminders.clear()


def test_reminder_store_persists_and_normalizes_to_utc(tmp_path):
    db = tmp_path / "reminders.db"
    first = ReminderStore(str(db))
    created = first.add("join review", "2026-08-13T16:00:00+05:30")
    second = ReminderStore(str(db))

    stored = second.list()[0]
    assert stored["id"] == created["id"]
    assert stored["due_at"] == "2026-08-13T10:30:00Z"
    assert stored["message"] == "join review"


def test_due_returns_only_open_due_reminders(tmp_path):
    store = ReminderStore(str(tmp_path / "due.db"))
    due = store.add("due now", "2026-08-13T10:00:00Z")
    store.add("later", "2026-08-13T12:00:00Z")
    dismissed = store.add("dismissed", "2026-08-13T09:00:00Z")
    store.dismiss(int(dismissed["id"]))

    result = store.due(datetime(2026, 8, 13, 10, 30, tzinfo=timezone.utc))
    assert [item["id"] for item in result] == [due["id"]]


def test_reminder_requires_explicit_timezone(tmp_path):
    store = ReminderStore(str(tmp_path / "timezone.db"))
    try:
        store.add("ambiguous", "2026-08-13T10:30:00")
    except ValueError as exc:
        assert "timezone" in str(exc).lower()
    else:
        raise AssertionError("timezone-less reminder must be rejected")


def test_add_list_and_dismiss_reminder_through_command_api():
    added = client.post(
        "/command",
        json={"command": "remind me at 2026-08-13T10:30:00Z to review Vayu CI"},
    )
    body = added.json()
    assert body["status"] == "ok"
    assert body["intent"] == "reminder_add"
    assert body["executed"] is True
    assert "review Vayu CI" in body["reply"]

    listed = client.post("/command", json={"command": "list reminders"})
    assert "review Vayu CI" in listed.json()["reply"]

    reminder_id = int(reminders.list()[0]["id"])
    dismissed = client.post(
        "/command",
        json={"command": f"dismiss reminder {reminder_id}"},
    )
    assert dismissed.json()["status"] == "ok"
    assert dismissed.json()["intent"] == "reminder_dismiss"
    assert reminders.list() == []


def test_reminder_endpoints_and_skill_registry():
    reminders.add("already due", "2020-01-01T00:00:00Z")
    reminders.add("future", "2999-01-01T00:00:00Z")

    all_open = client.get("/reminders")
    assert len(all_open.json()["reminders"]) == 2

    due = client.get("/reminders/due")
    assert [item["message"] for item in due.json()["reminders"]] == ["already due"]

    skills = client.get("/skills")
    names = {skill["name"] for skill in skills.json()["skills"]}
    assert {"reminder_add", "reminders", "reminder_dismiss"}.issubset(names)
