from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SimulationDisposition(str, Enum):
    READY = "ready"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class SimulationResult:
    disposition: SimulationDisposition
    preconditions: tuple[str, ...]
    expected_changes: tuple[str, ...]
    failure_modes: tuple[str, ...]
    rollback: str
    reversible: bool
    findings: tuple[str, ...] = ()

    @property
    def may_stage(self) -> bool:
        return self.disposition is SimulationDisposition.READY


@dataclass(frozen=True)
class ToolSimulationProfile:
    required_fields: tuple[str, ...]
    preconditions: tuple[str, ...]
    expected_changes: tuple[str, ...]
    failure_modes: tuple[str, ...]
    rollback: str
    reversible: bool


class CognitiveSimulator:
    """Deterministic, side-effect-free simulator for planner proposals.

    It predicts a bounded set of prerequisites, state changes, failure modes and
    rollback properties for explicitly allow-listed tools. It never calls tools,
    networks, models, stores, permission systems, or external services.
    """

    MAX_PAYLOAD_KEYS = 64
    MAX_TEXT = 2_000

    _PROFILES: dict[str, ToolSimulationProfile] = {
        "notification.send": ToolSimulationProfile(
            required_fields=("message",),
            preconditions=("notification adapter is configured", "recipient context is resolvable by the approved adapter"),
            expected_changes=("one external notification may be emitted after approval",),
            failure_modes=("adapter unavailable", "recipient unavailable", "downstream delivery rejected or delayed"),
            rollback="No reliable recall after delivery; prevent duplicates with action idempotency and require a new compensating notification if correction is needed.",
            reversible=False,
        ),
        "email.send": ToolSimulationProfile(
            required_fields=("to",),
            preconditions=("email adapter is configured", "recipient address is explicitly resolved", "human approval remains valid at execution time"),
            expected_changes=("one outbound email may be accepted by the configured provider after approval",),
            failure_modes=("provider unavailable", "recipient rejected", "timeout after ambiguous provider acceptance"),
            rollback="Email cannot be reliably recalled after provider acceptance; do not auto-retry ambiguous failures and use a separately approved corrective message if necessary.",
            reversible=False,
        ),
        "calendar.create": ToolSimulationProfile(
            required_fields=("title", "start"),
            preconditions=("calendar adapter is configured", "start time is explicit and timezone-aware", "human approval remains valid at execution time"),
            expected_changes=("one calendar event may be created after approval",),
            failure_modes=("provider unavailable", "invalid or conflicting time", "event created but response lost"),
            rollback="If creation returns a durable event identifier, a separately approved calendar delete/cancel action can compensate; ambiguous creation must be reconciled before retry.",
            reversible=True,
        ),
    }

    @staticmethod
    def _resolved(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True

    def simulate(self, *, tool: str, payload: dict[str, Any]) -> SimulationResult:
        if not isinstance(payload, dict):
            return SimulationResult(
                SimulationDisposition.BLOCKED,
                (), (), (), "Unavailable because payload is invalid.", False,
                ("simulation payload is not an object",),
            )
        if len(payload) > self.MAX_PAYLOAD_KEYS:
            return SimulationResult(
                SimulationDisposition.BLOCKED,
                (), (), (), "Unavailable because payload exceeds simulator bounds.", False,
                ("payload contains too many top-level fields",),
            )

        profile = self._PROFILES.get(tool)
        if profile is None:
            return SimulationResult(
                SimulationDisposition.BLOCKED,
                (), (), (), "No rollback model exists for this tool.", False,
                (f"tool '{tool}' has no explicit simulation profile",),
            )

        unresolved = tuple(field for field in profile.required_fields if not self._resolved(payload.get(field)))
        oversized = tuple(
            key for key, value in payload.items()
            if isinstance(value, str) and len(value) > self.MAX_TEXT
        )
        findings: list[str] = []
        findings.extend(f"required field '{field}' is unresolved" for field in unresolved)
        findings.extend(f"payload field '{field}' exceeds simulator text bound" for field in oversized)
        if findings:
            return SimulationResult(
                SimulationDisposition.NEEDS_REVISION,
                profile.preconditions,
                profile.expected_changes,
                profile.failure_modes,
                profile.rollback,
                profile.reversible,
                tuple(findings),
            )

        return SimulationResult(
            SimulationDisposition.READY,
            profile.preconditions,
            profile.expected_changes,
            profile.failure_modes,
            profile.rollback,
            profile.reversible,
            ("bounded deterministic simulation completed without objection",),
        )


simulator = CognitiveSimulator()
