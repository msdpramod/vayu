from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import os
from typing import Any

import httpx

from app.actions import PENDING, ProposedActionStore, actions
from app.payload_policy import validate_planner_payload
from app.plan_critic import PlanCritic, PlanCriticDisposition, plan_critic


PROPOSABLE_TOOLS = frozenset({
    "calendar.create",
    "email.send",
    "notification.send",
})


@dataclass(frozen=True)
class PlannedAction:
    tool: str
    description: str
    payload: dict[str, Any]
    risk: str = "confirm"


@dataclass(frozen=True)
class PlannerDecision:
    reply: str
    action: PlannedAction | None = None
    provider: str = "unknown"


class PlannerProvider(ABC):
    """Produces plans only. Providers never receive an executor or approval capability."""

    @abstractmethod
    def plan(self, prompt: str) -> PlannerDecision:
        raise NotImplementedError


class LocalRulePlanner(PlannerProvider):
    """Deterministic offline fallback for exercising the planner boundary safely."""

    def plan(self, prompt: str) -> PlannerDecision:
        text = prompt.strip()
        if not text.lower().startswith("propose ") or ":" not in text:
            return PlannerDecision(
                reply=(
                    "No external planner is configured. I can still stage an explicit "
                    "proposal using 'propose <tool>: <description>'."
                ),
                provider="local-rule",
            )

        head, description = text.split(":", 1)
        tool = head[len("propose "):].strip().lower()
        description = description.strip()
        return PlannerDecision(
            reply=f"Prepared a review-only proposal for {tool}.",
            action=PlannedAction(tool=tool, description=description, payload={}),
            provider="local-rule",
        )


class OllamaPlanner(PlannerProvider):
    """Local-LLM planner using strict JSON output; it can only propose actions."""

    def __init__(self, base_url: str, model: str, timeout_seconds: float = 8.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def plan(self, prompt: str) -> PlannerDecision:
        system = (
            "You are Vayu's planning component. Never claim an action was executed. "
            "Return one JSON object only with keys reply and action. action must be null "
            "or an object with tool, description, payload, risk. Allowed tools: "
            "calendar.create, email.send, notification.send. risk must always be confirm. "
            "Do not invent credentials, secrets, recipients, dates, or identifiers."
        )
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{system}\n\nUser request: {prompt}",
                    "format": "json",
                    "stream": False,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            envelope = response.json()
            raw = envelope.get("response")
            if not isinstance(raw, str):
                raise ValueError("Ollama response is missing the planner JSON string.")
            data = json.loads(raw)
        except (httpx.HTTPError, json.JSONDecodeError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Ollama planner unavailable or invalid: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError("Planner output must be a JSON object.")
        reply = data.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("Planner reply is required.")
        raw_action = data.get("action")
        if raw_action is None:
            return PlannerDecision(reply=reply.strip(), provider="ollama")
        if not isinstance(raw_action, dict):
            raise ValueError("Planner action must be an object or null.")
        allowed_keys = {"tool", "description", "payload", "risk"}
        if set(raw_action) - allowed_keys:
            raise ValueError("Planner action contains unsupported fields.")
        return PlannerDecision(
            reply=reply.strip(),
            action=PlannedAction(
                tool=str(raw_action.get("tool", "")),
                description=str(raw_action.get("description", "")),
                payload=raw_action.get("payload", {}),
                risk=str(raw_action.get("risk", "confirm")),
            ),
            provider="ollama",
        )


def get_planner_provider() -> PlannerProvider:
    provider = os.getenv("VAYU_PLANNER_PROVIDER", "local").strip().lower()
    if provider == "local":
        return LocalRulePlanner()
    if provider == "ollama":
        return OllamaPlanner(
            base_url=os.getenv("VAYU_OLLAMA_URL", "http://127.0.0.1:11434"),
            model=os.getenv("VAYU_OLLAMA_MODEL", "llama3.2"),
            timeout_seconds=float(os.getenv("VAYU_OLLAMA_TIMEOUT_SECONDS", "8")),
        )
    raise ValueError(f"Unsupported VAYU_PLANNER_PROVIDER: {provider}")


class PlannerService:
    """Validates and critiques plans before staging; it never approves or executes."""

    def __init__(
        self,
        store: ProposedActionStore,
        provider: PlannerProvider | None = None,
        proposable_tools: frozenset[str] = PROPOSABLE_TOOLS,
        critic: PlanCritic | None = None,
    ):
        self.store = store
        self.provider = provider or get_planner_provider()
        self.proposable_tools = proposable_tools
        self.critic = critic or plan_critic

    def _validate_action(self, action: PlannedAction) -> None:
        if action.tool not in self.proposable_tools:
            raise ValueError(f"Planner tool '{action.tool}' is not allow-listed for proposals.")
        if action.risk != "confirm":
            raise ValueError("Planner-created actions must require confirmation.")
        if not action.description.strip():
            raise ValueError("Planner action description is required.")
        if len(action.description) > 500:
            raise ValueError("Planner action description is too long.")
        validate_planner_payload(action.payload)

    def stage_decision(self, decision: PlannerDecision) -> dict[str, Any]:
        response: dict[str, Any] = {
            "provider": decision.provider,
            "reply": decision.reply,
            "plan_critique": None,
            "proposed_action": None,
        }
        if decision.action is None:
            return response

        self._validate_action(decision.action)
        critique = self.critic.review(
            tool=decision.action.tool,
            description=decision.action.description,
            payload=decision.action.payload,
            reply=decision.reply,
        )
        response["plan_critique"] = {
            "disposition": critique.disposition.value,
            "findings": list(critique.findings),
        }
        if critique.disposition is not PlanCriticDisposition.VERIFIED:
            return response

        proposed = self.store.propose(
            tool=decision.action.tool,
            description=decision.action.description,
            payload=decision.action.payload,
            risk="confirm",
        )
        if proposed["status"] != PENDING:
            raise RuntimeError("Planner proposal did not enter pending approval state.")
        response["proposed_action"] = proposed
        return response

    def plan(self, prompt: str) -> dict[str, Any]:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Planner prompt is required.")
        return self.stage_decision(self.provider.plan(prompt))


planner = PlannerService(actions)
