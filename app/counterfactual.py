from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.simulator import SimulationDisposition, SimulationResult
from app.world_model import WorldSnapshot


class CounterfactualDisposition(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"


class CounterfactualOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class PredictedFact:
    subject_id: str
    predicate: str
    value: str
    confidence: float


@dataclass(frozen=True)
class CounterfactualBranch:
    outcome: CounterfactualOutcome
    delta: tuple[PredictedFact, ...]
    requires_reconciliation: bool = False


@dataclass(frozen=True)
class CounterfactualWorld:
    """Ephemeral future alternatives layered over a read-only current snapshot.

    The object contains predicted deltas only. It has no persistence or execution
    capability and must never be written back to the World Model as observation.
    """

    disposition: CounterfactualDisposition
    branches: tuple[CounterfactualBranch, ...]
    invariants: tuple[str, ...]
    assumptions: tuple[str, ...]
    conflicts: tuple[str, ...] = ()
    base_snapshot_generated_at: str | None = None

    @property
    def may_stage(self) -> bool:
        return self.disposition is CounterfactualDisposition.READY


@dataclass(frozen=True)
class CounterfactualProfile:
    effect_subject: str
    success_value: str
    failure_value: str
    ambiguous_value: str


class CounterfactualSimulator:
    """Builds bounded alternative future-state deltas without mutating reality."""

    MAX_PAYLOAD_KEYS = 64
    MAX_BRANCHES = 3

    _PROFILES: dict[str, CounterfactualProfile] = {
        "email.send": CounterfactualProfile(
            effect_subject="effect:email.send",
            success_value="provider_accepted",
            failure_value="not_sent",
            ambiguous_value="delivery_state_unknown",
        ),
        "calendar.create": CounterfactualProfile(
            effect_subject="effect:calendar.create",
            success_value="event_created",
            failure_value="event_not_created",
            ambiguous_value="creation_state_unknown",
        ),
        "notification.send": CounterfactualProfile(
            effect_subject="effect:notification.send",
            success_value="notification_emitted",
            failure_value="notification_not_emitted",
            ambiguous_value="delivery_state_unknown",
        ),
    }

    def project(
        self,
        *,
        tool: str,
        payload: dict[str, Any],
        simulation: SimulationResult,
        world_snapshot: WorldSnapshot | None = None,
    ) -> CounterfactualWorld:
        timestamp = world_snapshot.generated_at if world_snapshot else simulation.snapshot_generated_at
        invariants = (
            "counterfactual state is ephemeral and must not be persisted as observation",
            "human approval remains required before any external action",
            "predicted outcomes never grant tool or executor authority",
        )

        if simulation.disposition is not SimulationDisposition.READY:
            return CounterfactualWorld(
                disposition=CounterfactualDisposition.BLOCKED,
                branches=(),
                invariants=invariants,
                assumptions=(),
                conflicts=("base simulation is not ready",),
                base_snapshot_generated_at=timestamp,
            )
        if not isinstance(payload, dict) or len(payload) > self.MAX_PAYLOAD_KEYS:
            return CounterfactualWorld(
                disposition=CounterfactualDisposition.BLOCKED,
                branches=(),
                invariants=invariants,
                assumptions=(),
                conflicts=("payload exceeds counterfactual bounds",),
                base_snapshot_generated_at=timestamp,
            )

        profile = self._PROFILES.get(tool)
        if profile is None:
            return CounterfactualWorld(
                disposition=CounterfactualDisposition.BLOCKED,
                branches=(),
                invariants=invariants,
                assumptions=(),
                conflicts=(f"tool '{tool}' has no counterfactual profile",),
                base_snapshot_generated_at=timestamp,
            )

        branches = (
            CounterfactualBranch(
                outcome=CounterfactualOutcome.SUCCESS,
                delta=(PredictedFact(profile.effect_subject, "external_state", profile.success_value, 0.60),),
            ),
            CounterfactualBranch(
                outcome=CounterfactualOutcome.FAILURE,
                delta=(PredictedFact(profile.effect_subject, "external_state", profile.failure_value, 0.60),),
            ),
            CounterfactualBranch(
                outcome=CounterfactualOutcome.AMBIGUOUS,
                delta=(PredictedFact(profile.effect_subject, "external_state", profile.ambiguous_value, 0.40),),
                requires_reconciliation=True,
            ),
        )
        if len(branches) > self.MAX_BRANCHES:
            return CounterfactualWorld(
                disposition=CounterfactualDisposition.BLOCKED,
                branches=(),
                invariants=invariants,
                assumptions=(),
                conflicts=("counterfactual branch limit exceeded",),
                base_snapshot_generated_at=timestamp,
            )

        assumptions = (
            "outcome probabilities are unknown; confidence labels express epistemic caution, not frequency",
            "external provider behavior is not observed during simulation",
        )
        if simulation.world_findings:
            assumptions += ("low-confidence current-world concerns remain unresolved",)

        return CounterfactualWorld(
            disposition=CounterfactualDisposition.READY,
            branches=branches,
            invariants=invariants,
            assumptions=assumptions,
            base_snapshot_generated_at=timestamp,
        )


counterfactual_simulator = CounterfactualSimulator()
