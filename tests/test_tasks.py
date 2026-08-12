from fastapi.testclient import TestClient

from app.main import app
from app.tasks import TaskStore, tasks

client = TestClient(app)


def setup_function():
    tasks.clear()


def test_task_store_persists_across_instances(tmp_path):
    db = tmp_path / "tasks.db"
    first = TaskStore(str(db))
    created = first.add("ship Vayu increment")
    second = TaskStore(str(db))
    assert second.list()[0]["id"] == created["id"]
    assert second.list()[0]["title"] == "ship Vayu increment"


def test_add_list_and_complete_task_through_command_api():
    added = client.post("/command", json={"command": "add task review CI"})
    body = added.json()
    assert body["status"] == "ok"
    assert body["intent"] == "task_add"
    assert body["executed"] is True

    listed = client.post("/command", json={"command": "list tasks"})
    assert "review CI" in listed.json()["reply"]

    task_id = tasks.list()[0]["id"]
    completed = client.post("/command", json={"command": f"complete task {task_id}"})
    assert completed.json()["status"] == "ok"
    assert completed.json()["intent"] == "task_complete"
    assert tasks.list() == []


def test_tasks_endpoint_can_include_completed_items():
    task = tasks.add("verify task API")
    tasks.complete(int(task["id"]))

    open_only = client.get("/tasks")
    assert open_only.json()["tasks"] == []

    all_items = client.get("/tasks?include_completed=true")
    assert all_items.json()["tasks"][0]["status"] == "completed"


def test_task_skill_is_explicitly_listed():
    response = client.get("/skills")
    names = {skill["name"] for skill in response.json()["skills"]}
    assert {"task_add", "tasks", "task_complete"}.issubset(names)
