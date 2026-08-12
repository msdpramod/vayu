from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.memory import memory
from app.permissions import Risk, classify
from app.providers import get_provider
from app.router import route
from app.skills import SKILLS, resolve

app = FastAPI(title="Vayu", version="0.3.0", description="Safe Jarvis-style assistant core")


class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)
    confirmed: bool = False


class CommandResponse(BaseModel):
    status: Literal["ok", "blocked", "confirmation_required", "unsupported"]
    intent: str
    reply: str
    executed: bool = False


@app.get("/")
def root():
    return {"name": "Vayu", "status": "running", "message": "Vayu assistant core is alive", "version": app.version}


@app.get("/health")
def health():
    return {"status": "ok", "service": "vayu", "version": app.version}


@app.get("/skills")
def skills():
    return {"skills": [{"name": skill.name, "description": skill.description} for skill in SKILLS.values()]}


@app.get("/memory")
def get_memory(limit: int = 10):
    return {"memories": memory.recent(limit)}


@app.post("/command", response_model=CommandResponse)
def command(req: CommandRequest):
    raw = req.command.strip()
    risk = classify(raw)

    if risk == Risk.BLOCKED:
        return CommandResponse(status="blocked", intent="high_risk_action", reply="Vayu blocked this high-risk command.")

    if risk == Risk.CONFIRM and not req.confirmed:
        return CommandResponse(status="confirmation_required", intent="sensitive_action", reply="This action requires explicit confirmation before execution.")

    skill = resolve(raw)
    if skill:
        return CommandResponse(status="ok", intent=skill.name, reply=skill.handler(raw), executed=True)

    intent = route(raw)
    if intent.name == "remember":
        if not intent.payload:
            return CommandResponse(status="unsupported", intent="remember", reply="Tell me what you want me to remember.")
        memory.add("user", intent.payload)
        return CommandResponse(status="ok", intent="remember", reply="I remembered that.", executed=True)

    if intent.name == "memory":
        items = memory.recent(10)
        if not items:
            return CommandResponse(status="ok", intent="memory", reply="I do not have any saved memories yet.", executed=True)
        summary = "; ".join(item["content"] for item in items)
        return CommandResponse(status="ok", intent="memory", reply=f"I remember: {summary}", executed=True)

    if intent.name == "skills":
        names = ", ".join(sorted(SKILLS))
        return CommandResponse(status="ok", intent="skills", reply=f"Installed skills: {names}.", executed=True)

    if risk == Risk.CONFIRM:
        return CommandResponse(status="unsupported", intent="sensitive_action", reply="Confirmed, but no executor skill is installed for this action yet.")

    brain = get_provider().reason(intent.payload)
    return CommandResponse(status="unsupported", intent="reason", reply=brain.text, executed=False)
