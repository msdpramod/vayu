from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Callable

from app.reminders import reminders
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


def add_reminder(command: str) -> str:
    match = re.match(r"^remind me at\s+(\S+)\s+to\s+(.+)$", command.strip(), flags=re.IGNORECASE)
    if not match:
        return "Use 'remind me at <ISO-8601 time> to <message>'."
    due_at, message = match.groups()
    try:
        reminder = reminders.add(message, due_at)
    except ValueError as exc:
        return str(exc)
    return f"Reminder {reminder['id']} set for {reminder['due_at']}: {reminder['message']}"


def list_reminders(_: str) -> str:
    items = reminders.list()
    if not items:
        return "You have no open reminders."
    summary = "; ".join(
        f"{item['id']} at {item['due_at']}: {item['message']}" for item in items
    )
    return f"Open reminders: {summary}"


def dismiss_reminder(command: str) -> str:
    payload = command.strip()[17:].strip()
    try:
        reminder_id = int(payload)
    except ValueError:
        return "Use 'dismiss reminder <id>' with a numeric reminder ID."
    reminder = reminders.dismiss(reminder_id)
    if reminder is None:
        return f"Reminder {reminder_id} does not exist."
    return f"Reminder {reminder_id} dismissed: {reminder['message']}"


SKILLS: dict[str, Skill] = {
    "hello": Skill("hello", "Greets the user", hello),
    "status": Skill("status", "Reports Vayu service status", status),
    "time": Skill("time", "Returns the current UTC time", current_time),
    "task_add": Skill("task_add", "Adds a durable local task", add_task),
    "tasks": Skill("tasks", "Lists open local tasks", list_tasks),
    "task_complete": Skill("task_complete", "Marks a local task complete", complete_task),
    "reminder_add": Skill("reminder_add", "Schedules a durable local reminder", add_reminder),
    "reminders": Skill("reminders", "Lists open local reminders", list_reminders),
    "reminder_dismiss": Skill("reminder_dismiss", "Dismisses a local reminder", dismiss_reminder),
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
    "list reminders": "reminders",
    "show reminders": "reminders",
    "my reminders": "reminders",
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
    if normalized.startswith("remind me at "):
        return SKILLS["reminder_add"]
    if normalized.startswith("dismiss reminder "):
        return SKILLS["reminder_dismiss"]
    return None
