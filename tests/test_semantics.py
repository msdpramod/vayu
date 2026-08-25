from datetime import datetime, timezone

import pytest

from app.attention import AttentionDecision, StimulusKind
from app.perception import PerceptionModality, PerceptionObservation
from app.semantics import SemanticFrame, SemanticSchema, SemanticUnderstandingBoundary


def _observation(*, confidence: float = 0.8, modality: PerceptionModality = PerceptionModality.DEVICE) -> PerceptionObservation:
    return PerceptionObservation(
        observation_id="obs-1",
        modality=modality,
        source="local-health",
        summary="API is degraded and requests are slow",
        observed_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
        importance=0.8,
        urgency=0.6,
        novelty=0.7,
        confidence=confidence,
    )


def _attention(*, salience: float = 0.72) -> AttentionDecision:
    return AttentionDecision(
        stimulus_id="obs-1",
        kind=StimulusKind.PERCEPTION,
        summary="API is degraded and requests are slow",
        salience=salience,
        should_interrupt=False,
        reason="selected for semantic processing",
    )


def _frame(*, confidence: float = 0.95, evidence_span: str = "API is degraded") -> SemanticFrame:
    return SemanticFrame(
        observation_id="obs-1",
        schema="device.service_status.v1",
        subject_id="service:api",
        predicate="status",
        value="degraded",
        confidence=confidence,
        evidence_span=evidence_span,
    )


def test_semantics_accepts_source_anchored_allowlisted_claim_and_caps_confidence():
    result = SemanticUnderstandingBoundary().interpret(
        observation=_observation(confidence=0.8),
        attention=_attention(),
        frame=_frame(confidence=0.95),
    )

    assert result.accepted is True
    assert result.candidate is not None
    assert result.candidate.subject_type == "service"
    assert result.candidate.predicate == "status"
    assert result.candidate.value == "degraded"
    assert result.candidate.confidence == 0.8


def test_semantics_abstains_when_claim_is_not_anchored_to_source():
    result = SemanticUnderstandingBoundary().interpret(
        observation=_observation(),
        attention=_attention(),
        frame=_frame(evidence_span="database is down"),
    )

    assert result.accepted is False
    assert result.candidate is None
    assert "not anchored" in result.reason


def test_semantics_rejects_predicate_and_value_outside_schema():
    boundary = SemanticUnderstandingBoundary()
    predicate_result = boundary.interpret(
        observation=_observation(),
        attention=_attention(),
        frame=SemanticFrame(
            observation_id="obs-1",
            schema="device.service_status.v1",
            subject_id="service:api",
            predicate="password",
            value="secret",
            confidence=0.9,
            evidence_span="API is degraded",
        ),
    )
    value_result = boundary.interpret(
        observation=_observation(),
        attention=_attention(),
        frame=SemanticFrame(
            observation_id="obs-1",
            schema="device.service_status.v1",
            subject_id="service:api",
            predicate="status",
            value="compromised",
            confidence=0.9,
            evidence_span="API is degraded",
        ),
    )

    assert predicate_result.accepted is False
    assert value_result.accepted is False


def test_semantics_abstains_on_low_confidence_or_low_salience():
    boundary = SemanticUnderstandingBoundary(minimum_confidence=0.55, minimum_salience=0.35)

    low_confidence = boundary.interpret(
        observation=_observation(confidence=0.4),
        attention=_attention(),
        frame=_frame(confidence=0.95),
    )
    low_salience = boundary.interpret(
        observation=_observation(),
        attention=_attention(salience=0.2),
        frame=_frame(),
    )

    assert low_confidence.accepted is False
    assert "confidence" in low_confidence.reason
    assert low_salience.accepted is False
    assert "salience" in low_salience.reason


def test_semantics_rejects_cross_observation_and_wrong_modality():
    boundary = SemanticUnderstandingBoundary()
    mismatched = SemanticFrame(
        observation_id="obs-other",
        schema="device.service_status.v1",
        subject_id="service:api",
        predicate="status",
        value="degraded",
        confidence=0.9,
        evidence_span="API is degraded",
    )

    with pytest.raises(ValueError):
        boundary.interpret(observation=_observation(), attention=_attention(), frame=mismatched)

    wrong_modality = boundary.interpret(
        observation=_observation(modality=PerceptionModality.BROWSER),
        attention=_attention(),
        frame=_frame(),
    )
    assert wrong_modality.accepted is False
    assert "modality" in wrong_modality.reason


def test_semantic_batch_is_bounded_and_rejects_duplicate_observations():
    boundary = SemanticUnderstandingBoundary()
    item = (_observation(), _attention(), _frame())

    with pytest.raises(ValueError):
        boundary.interpret_batch([item, item])

    with pytest.raises(ValueError):
        boundary.interpret_batch([item] * (boundary.MAX_FRAMES + 1))


def test_semantic_schema_registry_rejects_duplicate_names():
    schema = SemanticSchema(
        name="duplicate.v1",
        modality=PerceptionModality.DEVICE,
        subject_type="service",
        allowed_predicates=frozenset({"status"}),
        allowed_values={},
    )

    with pytest.raises(ValueError):
        SemanticUnderstandingBoundary(schemas=[schema, schema])
