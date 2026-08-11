from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Vayu", version="0.1.0", description="A safe Jarvis-style assistant backend MVP")


class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)


class CommandResponse(BaseModel):
    status: Literal["ok", "blocked", "unsupported"]
    intent: str
    reply: str
    executed: bool = False


SAFE_COMMANDS = {
    "time": "time",
    "what time is it": "time",
    "hello": "hello",
    "hi": "hello",
    "status": "status",
    "health": "status",
}

BLOCKED_TERMS = {
    "delete", "format", "shutdown", "reboot", "rm -rf", "wipe", "password", "credential",
    "transfer money", "pay ", "send money", "unlock", "disable security"
}


@app.get("/")
def root():
    return {
        "name": "Vayu",
        "status": "running",
        "message": "Vayu assistant backend is alive",
        "version": app.version,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "vayu", "version": app.version}


@app.post("/command", response_model=CommandResponse)
def command(req: CommandRequest):
    raw = req.command.strip()
    normalized = raw.lower()

    if any(term in normalized for term in BLOCKED_TERMS):
        return CommandResponse(
            status="blocked",
            intent="high_risk_action",
            reply="That action is blocked in the MVP. Vayu requires an explicit permission layer before executing destructive, financial, credential, or security-sensitive commands.",
            executed=False,
        )

    intent = SAFE_COMMANDS.get(normalized)
    if intent == "hello":
        return CommandResponse(status="ok", intent=intent, reply="Hello. Vayu is online.", executed=True)
    if intent == "status":
        return CommandResponse(status="ok", intent=intent, reply="Vayu is running normally.", executed=True)
    if intent == "time":
        now = datetime.now(timezone.utc).isoformat()
        return CommandResponse(status="ok", intent=intent, reply=f"Current UTC time is {now}.", executed=True)

    return CommandResponse(
        status="unsupported",
        intent="unknown",
        reply=(
            "I understood the request, but this MVP does not execute arbitrary operating-system commands yet. "
            "Add an allow-listed skill/plugin for the capability you want."
        ),
        executed=False,
    )
