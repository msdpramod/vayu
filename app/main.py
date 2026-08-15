from __future__ import annotations

import hashlib
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.actions import ActionExecutorRegistry, ProposedActionStore, actions, executors
from app.audit import audit
from app.confirmations import confirmations
from app.idempotency import idempotency
from app.memory import memory
from app.notifications import notifications
from app.permissions import Risk, classify
from app.planner import planner
from app.providers import get_provider
from app.reminders import reminders
from app.router import route
from app.skills import SKILLS, resolve
from app.tasks import tasks

app = FastAPI(title="Vayu", version="0.11.0", description="Safe Jarvis-style assistant core")


class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)
    confirmed: bool = False  # Deprecated: retained for client compatibility; never authorizes execution.
    confirmation_token: str | None = Field(default=None, min_length=16, max_length=256)
    request_id: str | None = Field(default=None, min_length=8, max_length=128)


class CommandResponse(BaseModel):
    status: Literal["ok", "blocked", "confirmation_required", "unsupported"]
    intent: str
    reply: str
    executed: bool = False
    confirmation_token: str | None = None


class ActionProposalRequest(BaseModel):
    tool: str = Field(min_length=3, max_length=64, pattern=r"^[a-z][a-z0-9_.-]+$")
    description: str = Field(min_length=3, max_length=500)
    payload: dict[str, Any] = Field(default_factory=dict)
    risk: Literal["safe", "confirm"] = "confirm"


class PlannerRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)


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


@app.get("/audit")
def get_audit(limit: int = 50):
    return {"events": audit.recent(limit)}


@app.get("/tasks")
def get_tasks(include_completed: bool = False, limit: int = 50):
    return {"tasks": tasks.list(include_completed=include_completed, limit=limit)}


@app.get("/reminders")
def get_reminders(include_dismissed: bool = False, limit: int = 50):
    return {"reminders": reminders.list(include_dismissed=include_dismissed, limit=limit)}


@app.get("/reminders/due")
def get_due_reminders(limit: int = 50):
    return {"reminders": reminders.due(limit=limit)}


@app.post("/reminders/dispatch")
def dispatch_due_reminders(limit: int = 50):
    return {"notifications": notifications.enqueue_due(reminders, limit=limit)}


@app.get("/notifications")
def get_notifications(limit: int = 50):
    return {"notifications": notifications.list(limit=limit)}


@app.post("/plan")
def create_plan(req: PlannerRequest):
    try:
        return planner.plan(req.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/actions", status_code=201)
def propose_action(req: ActionProposalRequest):
    try:
        return actions.propose(req.tool, req.description, req.payload, req.risk)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/actions")
def get_actions(status: str | None = None, limit: int = 50):
    return {"actions": actions.list(status=status, limit=limit)}


@app.get("/actions/{action_id}")
def get_action(action_id: int):
    try:
        return actions.get(action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/actions/{action_id}/events")
def get_action_events(action_id: int, limit: int = 100):
    try:
        return {"events": actions.events(action_id, limit=limit)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/actions/{action_id}/approve")
def approve_action(action_id: int):
    try:
        return actions.approve(action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/actions/{action_id}/reject")
def reject_action(action_id: int):
    try:
        return actions.reject(action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/actions/{action_id}/execute")
def execute_action(action_id: int):
    try:
        return executors.execute(action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


def _respond(
    raw: str,
    risk: Risk,
    status: str,
    intent: str,
    reply: str,
    executed: bool = False,
    confirmation_token: str | None = None,
) -> CommandResponse:
    audit.record(raw, risk.value, intent, status, executed)
    return CommandResponse(
        status=status,
        intent=intent,
        reply=reply,
        executed=executed,
        confirmation_token=confirmation_token,
    )


def _execute_command(raw: str, confirmation_token: str | None) -> CommandResponse:
    risk = classify(raw)

    if risk == Risk.BLOCKED:
        return _respond(raw, risk, "blocked", "high_risk_action", "Vayu blocked this high-risk command.")

    if risk == Risk.CONFIRM:
        if confirmation_token is None:
            token = confirmations.issue(raw)
            return _respond(
                raw,
                risk,
                "confirmation_required",
                "sensitive_action",
                "This action requires explicit confirmation. Resubmit the exact command with the one-time confirmation token.",
                confirmation_token=token,
            )
        if not confirmations.consume(confirmation_token, raw):
            token = confirmations.issue(raw)
            return _respond(
                raw,
                risk,
                "confirmation_required",
                "sensitive_action",
                "The confirmation token is invalid, expired, already used, or belongs to another command.",
                confirmation_token=token,
            )

    skill = resolve(raw)
    if skill:
        return _respond(raw, risk, "ok", skill.name, skill.handler(raw), executed=True)

    intent = route(raw)
    if intent.name == "remember":
        if not intent.payload:
            return _respond(raw, risk, "unsupported", "remember", "Tell me what you want me to remember.")
        memory.add("user", intent.payload)
        return _respond(raw, risk, "ok", "remember", "I remembered that.", executed=True)

    if intent.name == "memory":
        items = memory.recent(10)
        if not items:
            return _respond(raw, risk, "ok", "memory", "I do not have any saved memories yet.", executed=True)
        summary = "; ".join(item["content"] for item in items)
        return _respond(raw, risk, "ok", "memory", f"I remember: {summary}", executed=True)

    if intent.name == "skills":
        names = ", ".join(sorted(SKILLS))
        return _respond(raw, risk, "ok", "skills", f"Installed skills: {names}.", executed=True)

    if risk == Risk.CONFIRM:
        return _respond(
            raw,
            risk,
            "unsupported",
            "sensitive_action",
            "Confirmed, but no executor skill is installed for this action yet.",
        )

    brain = get_provider().reason(intent.payload)
    return _respond(raw, risk, "unsupported", "reason", brain.text, executed=False)


@app.post("/command", response_model=CommandResponse)
def command(req: CommandRequest):
    raw = req.command.strip()
    token_fingerprint = "none"
    if req.confirmation_token:
        token_fingerprint = hashlib.sha256(req.confirmation_token.encode("utf-8")).hexdigest()
    fingerprint = f"{raw}\nconfirmation_token_sha256={token_fingerprint}"

    if req.request_id:
        try:
            cached = idempotency.get(req.request_id, fingerprint)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if cached is not None:
            return CommandResponse(**cached)

    response = _execute_command(raw, req.confirmation_token)

    if req.request_id:
        idempotency.put(req.request_id, fingerprint, response.model_dump())

    return response
