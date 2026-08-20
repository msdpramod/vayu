import pytest

from app.evolution import (
    CapabilitySignal,
    CognitiveDomain,
    EvolutionEngine,
    baseline_signals,
)


def test_rejects_invalid_signal_score():
    with pytest.raises(ValueError):
        CapabilitySignal(CognitiveDomain.MEMORY, "bad", 1.1, "invalid")


def test_domain_scores_average_multiple_signals():
    engine = EvolutionEngine()
    signals = [
        CapabilitySignal(CognitiveDomain.MEMORY, "a", 0.4, "evidence a"),
        CapabilitySignal(CognitiveDomain.MEMORY, "b", 0.6, "evidence b"),
    ]
    assert engine.domain_scores(signals)[CognitiveDomain.MEMORY] == 0.5


def test_proposal_targets_weakest_domain_and_requires_review():
    engine = EvolutionEngine(target_score=0.85)
    proposal = engine.propose_next(baseline_signals())
    assert proposal is not None
    assert proposal.domain == CognitiveDomain.PERCEPTION
    assert proposal.requires_human_review is True
    assert proposal.priority > 0


def test_no_proposal_when_all_domains_meet_target():
    engine = EvolutionEngine(target_score=0.8)
    signals = [
        CapabilitySignal(CognitiveDomain.MEMORY, "memory", 0.9, "strong"),
        CapabilitySignal(CognitiveDomain.SAFETY, "safety", 0.95, "strong"),
    ]
    assert engine.propose_next(signals) is None
