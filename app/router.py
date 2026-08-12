from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    name: str
    payload: str = ""


def route(command: str) -> Intent:
    text = command.strip()
    normalized = text.lower()

    aliases = {
        "hello": "hello",
        "hi": "hello",
        "hey vayu": "hello",
        "status": "status",
        "health": "status",
        "time": "time",
        "what time is it": "time",
        "list skills": "skills",
        "what can you do": "skills",
        "list tasks": "tasks",
        "show tasks": "tasks",
        "my tasks": "tasks",
    }
    if normalized in aliases:
        return Intent(aliases[normalized])

    if normalized.startswith("remember "):
        return Intent("remember", text[9:].strip())
    if normalized in {"memory", "what do you remember"}:
        return Intent("memory")
    if normalized.startswith("add task "):
        return Intent("task_add", text[9:].strip())
    if normalized.startswith("complete task "):
        return Intent("task_complete", text[14:].strip())

    return Intent("reason", text)
