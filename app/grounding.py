from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.attention import AttentionDecision
from app.perception import PerceptionObservation
from app.world_model import WorldFact, WorldModel


@dataclass(frozen=True)
class GroundingCandidate:
    """Structured candidate knowledge derived from one perception observation.

    The grounding layer does not interpret arbitrary natural language and does not
    execute actions. A caller must provide an explicit structured candidate whose
    observation ID is bound to attended evidence.
    """

    observation_id: str
    subject_id: str
    subject_type: str
    predicate: str
    value: str
    confidence: float
    object_id: str | None = None
    object_type: str | None = None

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("observation_id is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class GroundingResult:
    observation_id: str
    grounded: bool
    reason: str
    fact: WorldFact | None = None


class CognitiveGroundingGateway:
    """Connects Perception -> Attention -> World Model without action authority.

    Only evidence that was actually selected by the attention subsystem can be
    grounded. Effective confidence is capped by both the sensory observation and
    the structured candidate, preventing a downstream extractor from manufacturing
    stronger certainty than the source evidence supports.
    """

    MAX_CANDIDATES = 32

    def __init__(self, world_model: WorldModel, minimum_salience: float = 0.35):
        if not 0.0 <= minimum_salience <= 1.0:
            raise ValueError("minimum_salience must be between 0 and 1")
        self.world_model = world_model
        self.minimum_salience = minimum_salience

    def ground(
        self,
        *,
        observation: PerceptionObservation,
        attention: AttentionDecision,
        candidate: GroundingCandidate,
    ) -> GroundingResult:
        if observation.observation_id != attention.stimulus_id:
            raise ValueError("attention decision does not belong to observation")
        if observation.observation_id != candidate.observation_id:
            raise ValueError("grounding candidate does not belong to observation")
        if attention.salience < self.minimum_salience:
            return GroundingResult(
                observation_id=observation.observation_id,
                grounded=False,
                reason="attention salience below grounding threshold",
            )

        effective_confidence = min(observation.confidence, candidate.confidence)
        if effective_confidence <= 0.0:
            return GroundingResult(
                observation_id=observation.observation_id,
                grounded=False,
                reason="evidence confidence is zero",
            )

        provenance = (
            f"perception:{observation.modality.value}:"
            f"{observation.source}:{observation.observation_id}"
        )
        fact = self.world_model.observe(
            subject_id=candidate.subject_id,
            subject_type=candidate.subject_type,
            predicate=candidate.predicate,
            value=candidate.value,
            confidence=effective_confidence,
            provenance=provenance,
            observed_at=observation.observed_at,
            object_id=candidate.object_id,
            object_type=candidate.object_type,
        )
        return GroundingResult(
            observation_id=observation.observation_id,
            grounded=True,
            reason="attended evidence grounded into world model",
            fact=fact,
        )

    def ground_batch(
        self,
        items: Iterable[tuple[PerceptionObservation, AttentionDecision, GroundingCandidate]],
    ) -> list[GroundingResult]:
        batch = list(items)
        if len(batch) > self.MAX_CANDIDATES:
            raise ValueError(f"at most {self.MAX_CANDIDATES} grounding candidates may be processed at once")

        seen: set[str] = set()
        results: list[GroundingResult] = []
        for observation, attention, candidate in batch:
            if observation.observation_id in seen:
                raise ValueError("observation_id values must be unique in grounding batch")
            seen.add(observation.observation_id)
            results.append(
                self.ground(
                    observation=observation,
                    attention=attention,
                    candidate=candidate,
                )
            )
        return results
