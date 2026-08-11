from fastapi.testclient import TestClient

from app.main import app
from app.permissions import Risk, classify

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_hello():
    response = client.post("/command", json={"command": "hello"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_blocked_command():
    response = client.post("/command", json={"command": "delete all files"})
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["executed"] is False


def test_confirmation_required():
    response = client.post("/command", json={"command": "shutdown"})
    assert response.status_code == 200
    assert response.json()["status"] == "confirm_required"


def test_permission_classifier():
    assert classify("hello") == Risk.SAFE
    assert classify("shutdown") == Risk.CONFIRM
    assert classify("rm -rf /") == Risk.BLOCKED


def test_skills_endpoint():
    response = client.get("/skills")
    assert response.status_code == 200
    names = {skill["name"] for skill in response.json()["skills"]}
    assert {"hello", "status", "time"}.issubset(names)
