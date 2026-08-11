from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "Vayu"
    assert r.json()["status"] == "running"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_safe_command():
    r = client.post("/command", json={"command": "hello"})
    assert r.status_code == 200
    assert r.json()["executed"] is True


def test_blocked_command():
    r = client.post("/command", json={"command": "delete all files"})
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"
    assert r.json()["executed"] is False
