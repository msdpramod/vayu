from app.simulator import CognitiveSimulator, SimulationDisposition
from app.world_model import WorldModel


def test_simulator_models_notification_without_side_effects():
    result = CognitiveSimulator().simulate(
        tool="notification.send",
        payload={"message": "Build completed"},
    )

    assert result.disposition is SimulationDisposition.READY
    assert result.may_stage is True
    assert result.reversible is False
    assert result.preconditions
    assert result.expected_changes
    assert result.failure_modes
    assert "cannot be reliably recalled" in result.rollback.lower() or "no reliable recall" in result.rollback.lower()


def test_simulator_requires_explicit_email_recipient():
    result = CognitiveSimulator().simulate(tool="email.send", payload={})

    assert result.disposition is SimulationDisposition.NEEDS_REVISION
    assert result.may_stage is False
    assert "required field 'to' is unresolved" in result.findings


def test_simulator_requires_calendar_title_and_start():
    result = CognitiveSimulator().simulate(
        tool="calendar.create",
        payload={"title": "Architecture review"},
    )

    assert result.disposition is SimulationDisposition.NEEDS_REVISION
    assert "required field 'start' is unresolved" in result.findings
    assert result.reversible is True
    assert "event identifier" in result.rollback.lower()


def test_simulator_blocks_unknown_tool_without_profile():
    result = CognitiveSimulator().simulate(
        tool="shell.exec",
        payload={"command": "echo unsafe"},
    )

    assert result.disposition is SimulationDisposition.BLOCKED
    assert result.may_stage is False
    assert "no explicit simulation profile" in result.findings[0]


def test_simulator_rejects_oversized_text():
    result = CognitiveSimulator().simulate(
        tool="notification.send",
        payload={"message": "x" * 2001},
    )

    assert result.disposition is SimulationDisposition.NEEDS_REVISION
    assert any("exceeds simulator text bound" in finding for finding in result.findings)


def test_simulator_blocks_staging_when_world_model_knows_adapter_is_offline(tmp_path):
    model = WorldModel(str(tmp_path / "world.db"))
    model.observe(
        subject_id="adapter:email",
        subject_type="adapter",
        predicate="status",
        value="offline",
        confidence=0.94,
        provenance="health-check",
    )
    simulator = CognitiveSimulator()
    snapshot = model.snapshot(simulator.context_subjects("email.send"))

    result = simulator.simulate(
        tool="email.send",
        payload={"to": "owner@example.com"},
        world_snapshot=snapshot,
    )

    assert result.disposition is SimulationDisposition.NEEDS_REVISION
    assert result.may_stage is False
    assert "current world state contradicts a required execution precondition" in result.findings
    assert any("adapter:email" in finding and "offline" in finding for finding in result.world_findings)
    assert result.snapshot_generated_at == snapshot.generated_at


def test_simulator_does_not_promote_low_confidence_world_concern_to_fact(tmp_path):
    model = WorldModel(str(tmp_path / "world.db"))
    model.observe(
        subject_id="adapter:notification",
        subject_type="adapter",
        predicate="availability",
        value="unavailable",
        confidence=0.42,
        provenance="stale-probe",
    )
    simulator = CognitiveSimulator()
    snapshot = model.snapshot(simulator.context_subjects("notification.send"))

    result = simulator.simulate(
        tool="notification.send",
        payload={"message": "Build completed"},
        world_snapshot=snapshot,
    )

    assert result.disposition is SimulationDisposition.READY
    assert result.may_stage is True
    assert result.world_findings
    assert "bounded read-only world snapshot checked" in result.findings
