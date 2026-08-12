from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from app.tasks import tasks


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    handler: Callable[[str], str]


def hello(_: str) -> str:
    return "Hello. Vayu is online."


def status(_: str) -> str:
    return "Vayu is running normally."


def current_time(_: str) -> str:
    return f"Current UTC time is {datetime.now(timezone.utc).isoformat()}."


def add_task(command: str) -> str:
    title = command.strip()[9:].strip()
    if not title:
        return "Tell me what task to add."
    task = tasks.add(title)
    return f"Task {task['id']} added: {task['title']}"


def list_tasks(_: str) -> str:
    items = tasks.list()
    if not items:
        return "You have no open tasks."
    summary = "; ".join(f"{item['id']}: {item['title']}" for item in reversed(items))
    return f"Open tasks: {summary}"


def complete_task(command: str) -> str:
    payload = command.strip()[14:].strip()
    try:
        task_id = int(payload)
    except ValueError:
        return "Use 'complete task <id>' with a numeric task ID."
    task = tasks.complete(task_id)
    if task is None:
        return f"Task {task_id} does not exist."
    return f"Task {task_id} completed: {task['title']}"


SKILLS: dict[str, Skill] = {
    "hello": Skill("hello", "Greets the user", hello),
    "status": Skill("status", "Reports Vayu service status", status),
    "time": Skill("time", "Returns the current UTC time", current_time),
    "task_add": Skill("task_add", "Adds a durable local task", add_task),
    "tasks": Skill("tasks", "Lists open local tasks", list_tasks),
    "task_complete": Skill("task_complete", "Marks a local task complete", complete_task),
}

ALIASES = {
    "hello": "hello",
    "hi": "hello",
    "hey vayu": "hello",
    "status": "status",
    "health": "status",
    "time": "time",
    "what time is it": "time",
    "list tasks": "tasks",
    "show tasks": "tasks",
    "my tasks": "tasks",
}


def resolve(command: str) -> Skill | None:
    normalized = command.strip().lower()
    name = ALIASES.get(normalized)
    if name:
        return SKILLS.get(name)
    if normalized.startswith("add task "):
        return SKILLS["task_add"]
    if normalized.startswith("complete task "):
        return SKILLS["task_complete"]
    return None
