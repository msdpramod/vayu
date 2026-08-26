from datetime import datetime, timezone

import pytest

from app.critic import CriticDisposition, SemanticCritic
from app.grounding import GroundingCandidate
from app.perception import PerceptionModality, PerceptionObservation
from app.semantics import SemanticResult
from app.world_model import WorldFact


def _observation(confidence: float = 0.8) -> PerceptionObservation:
    return PerceptionObservation(
        observation_id="obs-1",
        modality=PerceptionModality.DEVICE,
        source="local-health",
        summary="API is degraded",
        observed_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
        importance=0.8,
        urgency=0.6,
        novelty=0.5,
        confidence=confidence,
    )


def _semantic(*, confidence: float = 0.8, accepted: bool = True) -> SemanticResult:
    candidate = GroundingCandidate(
        observation_id="obs-1",
        subject_id="service:api",
        subject_type="service",
        predicate="status",
        value="degraded",
        confidence=confidence,
    )
    return SemanticResult("obs-1", accepted, "test", candidate if accepted else None)


def _fact(*, fact_id: int = 1, value: str = "healthy", confidence: float = 0.9, current: bool = True) -> WorldFact:
    return WorldFact(
        id=fact_id,
        subject_id="service:api",
        subject_type="service",
        predicate="status",
        value=value,
        object_id=None,
        confidence=confidence,
        provenance="device:health",
        observed_at="2026-08-27T00:00:00+00:00",
        valid_from="2026-08-27T00:00:00+00:00",
        valid_to=None if current else "2026-08-27T00:01:00+00:00",
        superseded_by=None,
    )


def test_critic_verifies_admissible_claim_without_conflict():
    verdict = SemanticCritic().verify(observation=_observation(), semantic=_semantic())

    assert verdict.disposition is CriticDisposition.VERIFIED
    assert verdict.accepted is True
    assert verdict.candidate is not None


def test_critic_abstains_when_semantic_boundary_abstained():
    verdict = SemanticCritic().verify(observation=_observation(), semantic=_semantic(accepted=False))

    assert verdict.disposition is CriticDisposition.ABSTAIN
    assert verdict.accepted is False


def test_critic_rejects_confidence_escalation_beyond_source():
    verdict = SemanticCritic().verify(
        observation=_observation(confidence=0.6),
        semantic=_semantic(confidence=0.8),
    )

    assert verdict.disposition is CriticDisposition.ABSTAIN
    assert "exceeds source" in verdict.reason


def test_critic_abstains_for_stronger_contradictory_world_evidence():
    verdict = SemanticCritic(conflict_margin=0.1).verify(
        observation=_observation(),
        semantic=_semantic(confidence=0.7),
        world_context=[_fact(confidence=0.9)],
    )

    assert verdict.disposition is CriticDisposition.ABSTAIN
    assert verdict.conflicting_fact_ids == (1,)


def test_critic_surfaces_close_conflict_instead_of_silently_overwriting():
    verdict = SemanticCritic(conflict_margin=0.1).verify(
        observation=_observation(),
        semantic=_semantic(confidence=0.8),
        world_context=[_fact(confidence=0.82)],
    )

    assert verdict.disposition is CriticDisposition.CONFLICT
    assert verdict.accepted is False
    assert verdict.conflicting_fact_ids == (1,)


def test_critic_ignores_historical_and_matching_current_evidence():
    verdict = SemanticCritic().verify(
        observation=_observation(),
        semantic=_semantic(confidence=0.8),
        world_context=[
            _fact(fact_id=1, value="healthy", confidence=0.99, current=False),
            _fact(fact_id=2, value="degraded", confidence=0.95, current=True),
        ],
    )

    assert verdict.disposition is CriticDisposition.VERIFIED


def test_critic_rejects_cross_observation_and_bounds_context():
    semantic = _semantic()
    wrong = SemanticResult("obs-other", True, "test", semantic.candidate)

    with pytest.raises(ValueError):
        SemanticCritic().verify(observation=_observation(), semantic=wrong)

    with pytest.raises(ValueError):
        SemanticCritic().verify(
            observation=_observation(),
            semantic=semantic,
            world_context=[_fact(fact_id=i) for i in range(SemanticCritic.MAX_CONTEXT_FACTS + 1)],
        )
