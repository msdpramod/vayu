from fastapi.testclient import TestClient

from app.audit import AuditStore, audit, redact_command
from app.main import app
from app.memory import ConversationMemory, memory
from app.permissions import Risk, classify
from app.router import route

client = TestClient(app)


def setup_function():
    memory.clear()
    audit.clear()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_hello_command():
    response = client.post("/command", json={"command": "hello"})
    assert response.status_code == 200
    assert response.json()["intent"] == "hello"


def test_destructive_command_is_blocked():
    response = client.post("/command", json={"command": "delete all files"})
    assert response.json()["status"] == "blocked"


def test_sensitive_command_requires_confirmation():
    response = client.post("/command", json={"command": "shutdown"})
    assert response.json()["status"] == "confirmation_required"


def test_remember_and_recall_through_api():
    saved = client.post("/command", json={"command": "remember my favorite editor is IntelliJ"})
    assert saved.json()["status"] == "ok"
    recalled = client.post("/command", json={"command": "what do you remember"})
    assert "my favorite editor is IntelliJ" in recalled.json()["reply"]


def test_memory_endpoint():
    client.post("/command", json={"command": "remember Vayu uses explicit skills"})
    response = client.get("/memory")
    assert response.status_code == 200
    assert response.json()["memories"][0]["content"] == "Vayu uses explicit skills"


def test_sqlite_memory_survives_new_instance(tmp_path):
    db = tmp_path / "memory.db"
    first = ConversationMemory(str(db))
    first.add("user", "persistent fact")
    second = ConversationMemory(str(db))
    assert second.recent(1)[0]["content"] == "persistent fact"


def test_unknown_command_routes_to_safe_brain_fallback():
    response = client.post("/command", json={"command": "explain quantum computing"})
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["intent"] == "reason"
    assert body["executed"] is False


def test_command_decision_is_audited():
    client.post("/command", json={"command": "hello"})
    events = client.get("/audit").json()["events"]
    assert len(events) == 1
    assert events[0]["command"] == "hello"
    assert events[0]["risk"] == "safe"
    assert events[0]["intent"] == "hello"
    assert events[0]["status"] == "ok"
    assert events[0]["executed"] is True


def test_blocked_command_is_audited():
    client.post("/command", json={"command": "delete all files"})
    event = client.get("/audit").json()["events"][0]
    assert event["risk"] == "blocked"
    assert event["status"] == "blocked"
    assert event["executed"] is False


def test_audit_redacts_secrets(tmp_path):
    db = tmp_path / "audit.db"
    store = AuditStore(str(db))
    store.record("call service token=abc123", "safe", "reason", "unsupported", False)
    event = store.recent(1)[0]
    assert "abc123" not in event["command"]
    assert "[REDACTED]" in event["command"]


def test_redaction_covers_common_secret_labels():
    assert "hunter2" not in redact_command("password=hunter2")
    assert "secret-value" not in redact_command("api_key: secret-value")


def test_router_memory_intent():
    intent = route("remember my favorite editor is IntelliJ")
    assert intent.name == "remember"
    assert intent.payload == "my favorite editor is IntelliJ"


def test_permission_classifier():
    assert classify("hello") == Risk.SAFE
    assert classify("shutdown") == Risk.CONFIRM
    assert classify("delete all files") == Risk.BLOCKED
