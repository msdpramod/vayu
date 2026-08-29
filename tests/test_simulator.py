from app.simulator import CognitiveSimulator, SimulationDisposition


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
