from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class PlanCriticDisposition(str, Enum):
    VERIFIED = "verified"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class PlanCriticResult:
    disposition: PlanCriticDisposition
    findings: tuple[str, ...]

    @property
    def may_stage(self) -> bool:
        return self.disposition is PlanCriticDisposition.VERIFIED


class PlanCritic:
    """Deterministic second-pass critic for planner proposals.

    The critic is cognition-only. It cannot persist, approve, execute, call tools,
    access networks, or mutate planner output. It only decides whether a proposed
    action is sufficiently coherent to enter the existing human approval queue.
    """

    MAX_DESCRIPTION = 500
    MAX_REPLY = 2_000
    MAX_PAYLOAD_KEYS = 64

    _BLOCKED_PHRASES = (
        "bypass approval",
        "skip approval",
        "disable safety",
        "ignore safety",
        "without confirmation",
        "rm -rf",
        "drop database",
        "delete account",
        "wire money",
        "transfer funds",
        "purchase without approval",
    )

    _UNCERTAINTY_PHRASES = (
        "i guess",
        "not sure",
        "unknown recipient",
        "unknown date",
        "assume recipient",
        "assume date",
        "use whatever",
        "pick any",
        "tbd",
        "to be decided",
    )

    _EXECUTION_CLAIM_PHRASES = (
        "i sent ",
        "i created ",
        "i notified ",
        "already sent",
        "already created",
        "has been sent",
        "has been created",
        "executed successfully",
    )

    @staticmethod
    def _normalise(value: str) -> str:
        return " ".join(value.casefold().strip().split())

    @classmethod
    def _payload_findings(cls, payload: dict[str, Any]) -> list[str]:
        findings: list[str] = []
        if len(payload) > cls.MAX_PAYLOAD_KEYS:
            findings.append("payload contains too many top-level fields")
        for key, value in payload.items():
            if not isinstance(key, str) or not key.strip():
                findings.append("payload contains an invalid field name")
                continue
            if value is None:
                findings.append(f"payload field '{key}' is unresolved")
            elif isinstance(value, str) and not value.strip():
                findings.append(f"payload field '{key}' is empty")
        return findings

    def review(
        self,
        *,
        tool: str,
        description: str,
        payload: dict[str, Any],
        reply: str,
    ) -> PlanCriticResult:
        if not isinstance(payload, dict):
            return PlanCriticResult(
                PlanCriticDisposition.BLOCKED,
                ("planner payload is not an object",),
            )

        description_text = self._normalise(description)
        reply_text = self._normalise(reply)
        combined = f"{description_text} {reply_text}".strip()

        blocked: list[str] = []
        if len(description) > self.MAX_DESCRIPTION:
            blocked.append("description exceeds critic bound")
        if len(reply) > self.MAX_REPLY:
            blocked.append("planner reply exceeds critic bound")
        if not tool.strip():
            blocked.append("tool is missing")
        for phrase in self._BLOCKED_PHRASES:
            if phrase in combined:
                blocked.append(f"unsafe planner intent detected: '{phrase}'")
        for phrase in self._EXECUTION_CLAIM_PHRASES:
            if phrase in reply_text:
                blocked.append(f"planner falsely claims external execution: '{phrase}'")

        if blocked:
            return PlanCriticResult(PlanCriticDisposition.BLOCKED, tuple(dict.fromkeys(blocked)))

        revisions = self._payload_findings(payload)
        for phrase in self._UNCERTAINTY_PHRASES:
            if phrase in combined:
                revisions.append(f"unresolved planner uncertainty detected: '{phrase}'")

        if revisions:
            return PlanCriticResult(
                PlanCriticDisposition.NEEDS_REVISION,
                tuple(dict.fromkeys(revisions)),
            )

        return PlanCriticResult(
            PlanCriticDisposition.VERIFIED,
            ("no deterministic planner-critic objection",),
        )


plan_critic = PlanCritic()
