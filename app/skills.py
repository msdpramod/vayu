from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


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


SKILLS: dict[str, Skill] = {
    "hello": Skill("hello", "Greets the user", hello),
    "status": Skill("status", "Reports Vayu service status", status),
    "time": Skill("time", "Returns the current UTC time", current_time),
}

ALIASES = {
    "hello": "hello",
    "hi": "hello",
    "hey vayu": "hello",
    "status": "status",
    "health": "status",
    "time": "time",
    "what time is it": "time",
}


def resolve(command: str) -> Skill | None:
    name = ALIASES.get(command.strip().lower())
    return SKILLS.get(name) if name else None
