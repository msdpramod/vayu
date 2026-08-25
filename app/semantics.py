from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from app.attention import AttentionDecision
from app.grounding import GroundingCandidate
from app.perception import PerceptionModality, PerceptionObservation


@dataclass(frozen=True)
class SemanticSchema:
    """Allow-listed semantic shape for one class of sensory evidence."""

    name: str
    modality: PerceptionModality
    subject_type: str
    allowed_predicates: frozenset[str]
    allowed_values: Mapping[str, frozenset[str]]

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.subject_type.strip():
            raise ValueError("schema name and subject_type are required")
        if not self.allowed_predicates:
            raise ValueError("schema must allow at least one predicate")
        if set(self.allowed_values) - set(self.allowed_predicates):
            raise ValueError("allowed_values contains an unknown predicate")


@dataclass(frozen=True)
class SemanticFrame:
    """A proposed meaning for one observation; never executable authority."""

    observation_id: str
    schema: str
    subject_id: str
    predicate: str
    value: str
    confidence: float
    evidence_span: str
    object_id: str | None = None
    object_type: str | None = None

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("observation_id is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class SemanticResult:
    observation_id: str
    accepted: bool
    reason: str
    candidate: GroundingCandidate | None = None


DEFAULT_SCHEMAS = (
    SemanticSchema(
        name="device.service_status.v1",
        modality=PerceptionModality.DEVICE,
        subject_type="service",
        allowed_predicates=frozenset({"status"}),
        allowed_values={"status": frozenset({"healthy", "degraded", "down", "unknown"})},
    ),
    SemanticSchema(
        name="browser.page_state.v1",
        modality=PerceptionModality.BROWSER,
        subject_type="page",
        allowed_predicates=frozenset({"state"}),
        allowed_values={"state": frozenset({"loading", "ready", "error"})},
    ),
    SemanticSchema(
        name="file.lifecycle.v1",
        modality=PerceptionModality.FILE,
        subject_type="file",
        allowed_predicates=frozenset({"state"}),
        allowed_values={"state": frozenset({"created", "modified", "deleted"})},
    ),
)


class SemanticUnderstandingBoundary:
    """Validates proposed semantics before they may reach cognitive grounding.

    Providers, including future LLM extractors, may propose ``SemanticFrame`` values,
    but this boundary only accepts allow-listed schemas, source-anchored evidence and
    sufficient confidence. It has no model, network, planner, executor, permission,
    action-store or persistence capability.
    """

    MAX_FRAMES = 32
    MAX_SUBJECT_ID = 128
    MAX_EVIDENCE_SPAN = 160

    def __init__(
        self,
        schemas: Iterable[SemanticSchema] = DEFAULT_SCHEMAS,
        *,
        minimum_confidence: float = 0.55,
        minimum_salience: float = 0.35,
    ):
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")
        if not 0.0 <= minimum_salience <= 1.0:
            raise ValueError("minimum_salience must be between 0 and 1")
        schema_map = {schema.name: schema for schema in schemas}
        if not schema_map:
            raise ValueError("at least one semantic schema is required")
        if len(schema_map) != len(list(schema_map.values())):
            raise ValueError("semantic schema names must be unique")
        self.schemas = schema_map
        self.minimum_confidence = minimum_confidence
        self.minimum_salience = minimum_salience

    @staticmethod
    def _normalized(value: str) -> str:
        return " ".join(value.casefold().split())

    def interpret(
        self,
        *,
        observation: PerceptionObservation,
        attention: AttentionDecision,
        frame: SemanticFrame,
    ) -> SemanticResult:
        if observation.observation_id != attention.stimulus_id:
            raise ValueError("attention decision does not belong to observation")
        if observation.observation_id != frame.observation_id:
            raise ValueError("semantic frame does not belong to observation")
        if attention.salience < self.minimum_salience:
            return SemanticResult(frame.observation_id, False, "attention salience below semantic threshold")

        schema = self.schemas.get(frame.schema)
        if schema is None:
            return SemanticResult(frame.observation_id, False, "semantic schema is not allow-listed")
        if schema.modality != observation.modality:
            return SemanticResult(frame.observation_id, False, "semantic schema does not match observation modality")
        if frame.predicate not in schema.allowed_predicates:
            return SemanticResult(frame.observation_id, False, "predicate is not allowed by semantic schema")

        allowed = schema.allowed_values.get(frame.predicate)
        if allowed is not None and frame.value not in allowed:
            return SemanticResult(frame.observation_id, False, "value is not allowed by semantic schema")

        subject_id = frame.subject_id.strip()
        if not subject_id or len(subject_id) > self.MAX_SUBJECT_ID:
            return SemanticResult(frame.observation_id, False, "subject_id is invalid")

        evidence_span = frame.evidence_span.strip()
        if not evidence_span or len(evidence_span) > self.MAX_EVIDENCE_SPAN:
            return SemanticResult(frame.observation_id, False, "evidence_span is invalid")
        if self._normalized(evidence_span) not in self._normalized(observation.summary):
            return SemanticResult(frame.observation_id, False, "semantic claim is not anchored to source evidence")

        effective_confidence = min(observation.confidence, frame.confidence)
        if effective_confidence < self.minimum_confidence:
            return SemanticResult(frame.observation_id, False, "semantic evidence confidence is below threshold")

        if frame.object_id is not None and frame.object_type is None:
            return SemanticResult(frame.observation_id, False, "object_type is required when object_id is present")
        if frame.object_id is None and frame.object_type is not None:
            return SemanticResult(frame.observation_id, False, "object_id is required when object_type is present")

        candidate = GroundingCandidate(
            observation_id=frame.observation_id,
            subject_id=subject_id,
            subject_type=schema.subject_type,
            predicate=frame.predicate,
            value=frame.value,
            confidence=effective_confidence,
            object_id=frame.object_id,
            object_type=frame.object_type,
        )
        return SemanticResult(frame.observation_id, True, "schema-constrained semantics accepted", candidate)

    def interpret_batch(
        self,
        items: Iterable[tuple[PerceptionObservation, AttentionDecision, SemanticFrame]],
    ) -> list[SemanticResult]:
        batch = list(items)
        if len(batch) > self.MAX_FRAMES:
            raise ValueError(f"at most {self.MAX_FRAMES} semantic frames may be processed at once")

        seen: set[str] = set()
        results: list[SemanticResult] = []
        for observation, attention, frame in batch:
            if observation.observation_id in seen:
                raise ValueError("observation_id values must be unique in semantic batch")
            seen.add(observation.observation_id)
            results.append(self.interpret(observation=observation, attention=attention, frame=frame))
        return results
