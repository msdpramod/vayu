from datetime import datetime, timezone

import pytest

from app.world_model import WorldModel


def test_world_model_persists_current_fact_and_relationship(tmp_path):
    db = tmp_path / "vayu.db"
    model = WorldModel(str(db))

    fact = model.observe(
        subject_id="project:vayu",
        subject_type="project",
        predicate="depends_on",
        value="ollama",
        object_id="service:ollama",
        object_type="service",
        confidence=0.9,
        provenance="repo-config",
        observed_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
    )

    assert fact.is_current
    reopened = WorldModel(str(db))
    current = reopened.current("project:vayu", "depends_on")
    assert len(current) == 1
    assert current[0].object_id == "service:ollama"
    assert {entity["entity_id"] for entity in reopened.entities()} == {"project:vayu", "service:ollama"}


def test_higher_confidence_contradiction_supersedes_but_keeps_history(tmp_path):
    model = WorldModel(str(tmp_path / "vayu.db"))
    first = model.observe(
        subject_id="service:api",
        subject_type="service",
        predicate="status",
        value="healthy",
        confidence=0.55,
        provenance="cached-health",
    )
    second = model.observe(
        subject_id="service:api",
        subject_type="service",
        predicate="status",
        value="degraded",
        confidence=0.92,
        provenance="live-health",
    )

    current = model.current("service:api", "status")
    history = model.history("service:api", "status")

    assert [fact.value for fact in current] == ["degraded"]
    assert history[0].id == second.id
    assert history[1].id == first.id
    assert history[1].superseded_by == second.id
    assert history[1].valid_to is not None


def test_lower_confidence_contradiction_does_not_replace_current_belief(tmp_path):
    model = WorldModel(str(tmp_path / "vayu.db"))
    model.observe(
        subject_id="device:mac",
        subject_type="device",
        predicate="online",
        value="true",
        confidence=0.95,
        provenance="local-agent",
    )
    weak = model.observe(
        subject_id="device:mac",
        subject_type="device",
        predicate="online",
        value="false",
        confidence=0.3,
        provenance="stale-cache",
    )

    assert weak.is_current is False
    assert model.current("device:mac", "online")[0].value == "true"
    assert len(model.history("device:mac", "online")) == 2


def test_same_claim_can_strengthen_confidence_without_duplicate_fact(tmp_path):
    model = WorldModel(str(tmp_path / "vayu.db"))
    first = model.observe(
        subject_id="repo:vayu",
        subject_type="repository",
        predicate="branch",
        value="main",
        confidence=0.6,
        provenance="memory",
    )
    second = model.observe(
        subject_id="repo:vayu",
        subject_type="repository",
        predicate="branch",
        value="main",
        confidence=0.9,
        provenance="github",
    )

    assert first.id == second.id
    assert second.confidence == 0.9
    assert second.provenance == "github"
    assert len(model.history("repo:vayu", "branch")) == 1


def test_world_model_rejects_invalid_or_ambiguous_evidence(tmp_path):
    model = WorldModel(str(tmp_path / "vayu.db"))

    with pytest.raises(ValueError):
        model.observe(
            subject_id="x",
            subject_type="device",
            predicate="status",
            value="ok",
            confidence=1.1,
            provenance="sensor",
        )

    with pytest.raises(ValueError):
        model.observe(
            subject_id="x",
            subject_type="device",
            predicate="linked_to",
            value="y",
            object_id="y",
            confidence=0.8,
            provenance="sensor",
        )

    with pytest.raises(ValueError):
        model.observe(
            subject_id="x",
            subject_type="device",
            predicate="status",
            value="ok",
            confidence=0.8,
            provenance="sensor",
            observed_at="2026-08-24T01:00:00",
        )


def test_entity_type_is_stable_for_existing_identity(tmp_path):
    model = WorldModel(str(tmp_path / "vayu.db"))
    model.observe(
        subject_id="vayu",
        subject_type="assistant",
        predicate="state",
        value="ready",
        confidence=0.9,
        provenance="self",
    )

    with pytest.raises(ValueError):
        model.observe(
            subject_id="vayu",
            subject_type="device",
            predicate="state",
            value="ready",
            confidence=0.9,
            provenance="self",
        )
