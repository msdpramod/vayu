from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from app.grounding import GroundingCandidate
from app.perception import PerceptionObservation
from app.semantics import SemanticResult
from app.world_model import WorldFact


class CriticDisposition(str, Enum):
    VERIFIED = "verified"
    ABSTAIN = "abstain"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class CriticVerdict:
    observation_id: str
    disposition: CriticDisposition
    reason: str
    candidate: GroundingCandidate | None = None
    conflicting_fact_ids: tuple[int, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.disposition is CriticDisposition.VERIFIED and self.candidate is not None


class SemanticCritic:
    """Second-pass verifier for semantic claims before durable grounding.

    The semantic boundary validates whether a proposed meaning is structurally and
    evidentially admissible. The critic independently checks that accepted output
    remains bound to the source observation and does not silently displace stronger
    contradictory world knowledge. It is cognition-only: no model, network, planner,
    executor, permission, approval, or persistence authority is available here.
    """

    MAX_CONTEXT_FACTS = 32

    def __init__(self, *, conflict_margin: float = 0.10):
        if not 0.0 <= conflict_margin <= 1.0:
            raise ValueError("conflict_margin must be between 0 and 1")
        self.conflict_margin = conflict_margin

    def verify(
        self,
        *,
        observation: PerceptionObservation,
        semantic: SemanticResult,
        world_context: Iterable[WorldFact] = (),
    ) -> CriticVerdict:
        if semantic.observation_id != observation.observation_id:
            raise ValueError("semantic result does not belong to observation")

        candidate = semantic.candidate
        if not semantic.accepted or candidate is None:
            return CriticVerdict(
                observation.observation_id,
                CriticDisposition.ABSTAIN,
                "semantic boundary did not produce an admissible candidate",
            )
        if candidate.observation_id != observation.observation_id:
            raise ValueError("grounding candidate does not belong to observation")
        if candidate.confidence > observation.confidence:
            return CriticVerdict(
                observation.observation_id,
                CriticDisposition.ABSTAIN,
                "candidate confidence exceeds source evidence confidence",
            )

        facts = list(world_context)
        if len(facts) > self.MAX_CONTEXT_FACTS:
            raise ValueError(f"at most {self.MAX_CONTEXT_FACTS} world facts may be reviewed at once")

        conflicts: list[WorldFact] = []
        for fact in facts:
            if not fact.is_current:
                continue
            if fact.subject_id != candidate.subject_id or fact.predicate != candidate.predicate:
                continue
            same_claim = fact.value == candidate.value and fact.object_id == candidate.object_id
            if not same_claim:
                conflicts.append(fact)

        if conflicts:
            strongest = max(conflicts, key=lambda fact: fact.confidence)
            ids = tuple(sorted(fact.id for fact in conflicts))
            if strongest.confidence >= candidate.confidence + self.conflict_margin:
                return CriticVerdict(
                    observation.observation_id,
                    CriticDisposition.ABSTAIN,
                    "stronger contradictory world evidence requires new corroboration",
                    conflicting_fact_ids=ids,
                )
            return CriticVerdict(
                observation.observation_id,
                CriticDisposition.CONFLICT,
                "credible contradictory evidence requires explicit resolution before grounding",
                conflicting_fact_ids=ids,
            )

        return CriticVerdict(
            observation.observation_id,
            CriticDisposition.VERIFIED,
            "semantic claim survived independent source and world-context verification",
            candidate=candidate,
        )
