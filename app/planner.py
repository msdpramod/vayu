from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.actions import PENDING, ProposedActionStore, actions


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
    """Deterministic offline fallback for exercising the planner boundary safely.

    It recognizes only the explicit form:
        propose <allow-listed-tool>: <description>

    The rule intentionally does not infer recipients, credentials, shell commands,
    or side effects. It can only create a pending proposal for later human review.
    """

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


class PlannerService:
    """Validates planner output and stages, but never approves or executes, actions."""

    def __init__(
        self,
        store: ProposedActionStore,
        provider: PlannerProvider | None = None,
        proposable_tools: frozenset[str] = PROPOSABLE_TOOLS,
    ):
        self.store = store
        self.provider = provider or LocalRulePlanner()
        self.proposable_tools = proposable_tools

    def _validate_action(self, action: PlannedAction) -> None:
        if action.tool not in self.proposable_tools:
            raise ValueError(f"Planner tool '{action.tool}' is not allow-listed for proposals.")
        if action.risk != "confirm":
            raise ValueError("Planner-created actions must require confirmation.")
        if not action.description.strip():
            raise ValueError("Planner action description is required.")
        if len(action.description) > 500:
            raise ValueError("Planner action description is too long.")
        if not isinstance(action.payload, dict):
            raise ValueError("Planner action payload must be an object.")

    def stage_decision(self, decision: PlannerDecision) -> dict[str, Any]:
        response: dict[str, Any] = {
            "provider": decision.provider,
            "reply": decision.reply,
            "proposed_action": None,
        }
        if decision.action is None:
            return response

        self._validate_action(decision.action)
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
