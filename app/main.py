from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.permissions import Risk, classify
from app.skills import SKILLS, resolve

app = FastAPI(title="Vayu", version="0.2.0", description="Safe Jarvis-style assistant core")


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

    if risk == Risk.CONFIRM:
        return CommandResponse(status="unsupported", intent="sensitive_action", reply="Confirmed, but no executor skill is installed for this action yet.")

    return CommandResponse(status="unsupported", intent="unknown", reply="No installed Vayu skill can execute this command yet.")
