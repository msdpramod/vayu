from fastapi.testclient import TestClient

from app.main import app
from app.permissions import Risk, classify
from app.router import route

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_hello_command():
    response = client.post("/command", json={"command": "hello"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["intent"] == "hello"


def test_destructive_command_is_blocked():
    response = client.post("/command", json={"command": "delete all files"})
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"


def test_sensitive_command_requires_confirmation():
    response = client.post("/command", json={"command": "shutdown"})
    assert response.status_code == 200
    assert response.json()["status"] == "confirmation_required"


def test_router_memory_intent():
    intent = route("remember my favorite editor is IntelliJ")
    assert intent.name == "remember"
    assert intent.payload == "my favorite editor is IntelliJ"


def test_permission_classifier():
    assert classify("hello") == Risk.SAFE
    assert classify("shutdown") == Risk.CONFIRM
    assert classify("delete all files") == Risk.BLOCKED
