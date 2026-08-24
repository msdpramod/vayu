from datetime import datetime, timezone

import pytest

from app.attention import AttentionDecision, StimulusKind
from app.grounding import CognitiveGroundingGateway, GroundingCandidate
from app.perception import PerceptionModality, PerceptionObservation
from app.world_model import WorldModel


def _observation(confidence: float = 0.8) -> PerceptionObservation:
    return PerceptionObservation(
        observation_id="obs-1",
        modality=PerceptionModality.DEVICE,
        source="local-health",
        summary="API is degraded",
        observed_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        importance=0.8,
        urgency=0.6,
        novelty=0.7,
        confidence=confidence,
    )


def _decision(salience: float = 0.72) -> AttentionDecision:
    return AttentionDecision(
        stimulus_id="obs-1",
        kind=StimulusKind.PERCEPTION,
        summary="API is degraded",
        salience=salience,
        should_interrupt=False,
        reason="selected for cognitive processing",
    )


def _candidate(confidence: float = 0.95) -> GroundingCandidate:
    return GroundingCandidate(
        observation_id="obs-1",
        subject_id="service:api",
        subject_type="service",
        predicate="status",
        value="degraded",
        confidence=confidence,
    )


def test_attended_evidence_is_grounded_with_confidence_capped_by_source(tmp_path):
    world = WorldModel(str(tmp_path / "vayu.db"))
    gateway = CognitiveGroundingGateway(world)

    result = gateway.ground(
        observation=_observation(confidence=0.8),
        attention=_decision(),
        candidate=_candidate(confidence=0.95),
    )

    assert result.grounded is True
    assert result.fact is not None
    assert result.fact.confidence == 0.8
    assert result.fact.provenance == "perception:device:local-health:obs-1"
    assert world.current("service:api", "status")[0].value == "degraded"


def test_low_salience_evidence_is_not_persisted(tmp_path):
    world = WorldModel(str(tmp_path / "vayu.db"))
    gateway = CognitiveGroundingGateway(world, minimum_salience=0.5)

    result = gateway.ground(
        observation=_observation(),
        attention=_decision(salience=0.2),
        candidate=_candidate(),
    )

    assert result.grounded is False
    assert world.current("service:api", "status") == []


def test_grounding_rejects_cross_observation_binding(tmp_path):
    world = WorldModel(str(tmp_path / "vayu.db"))
    gateway = CognitiveGroundingGateway(world)
    mismatched = GroundingCandidate(
        observation_id="obs-other",
        subject_id="service:api",
        subject_type="service",
        predicate="status",
        value="degraded",
        confidence=0.9,
    )

    with pytest.raises(ValueError):
        gateway.ground(
            observation=_observation(),
            attention=_decision(),
            candidate=mismatched,
        )


def test_grounding_batch_is_bounded_and_rejects_duplicate_observations(tmp_path):
    world = WorldModel(str(tmp_path / "vayu.db"))
    gateway = CognitiveGroundingGateway(world)
    item = (_observation(), _decision(), _candidate())

    with pytest.raises(ValueError):
        gateway.ground_batch([item, item])

    with pytest.raises(ValueError):
        gateway.ground_batch([item] * (gateway.MAX_CANDIDATES + 1))
