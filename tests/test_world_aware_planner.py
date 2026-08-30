from app.actions import ProposedActionStore
from app.planner import PlannedAction, PlannerDecision, PlannerProvider, PlannerService
from app.world_model import WorldModel


class FixedPlanner(PlannerProvider):
    def __init__(self, decision: PlannerDecision):
        self.decision = decision

    def plan(self, prompt: str) -> PlannerDecision:
        return self.decision


def test_planner_does_not_stage_action_when_world_state_breaks_precondition(tmp_path):
    store = ProposedActionStore(str(tmp_path / "actions.db"))
    world = WorldModel(str(tmp_path / "world.db"))
    world.observe(
        subject_id="adapter:email",
        subject_type="adapter",
        predicate="availability",
        value="unavailable",
        confidence=0.97,
        provenance="adapter-health",
    )
    decision = PlannerDecision(
        reply="I prepared the email for review.",
        action=PlannedAction(
            tool="email.send",
            description="Send the reviewed status update",
            payload={"to": "owner@example.com"},
        ),
        provider="test-planner",
    )
    service = PlannerService(store, FixedPlanner(decision), world_model=world)

    result = service.plan("send the reviewed status update")

    assert result["plan_critique"]["disposition"] == "verified"
    assert result["simulation"]["disposition"] == "needs_revision"
    assert result["simulation"]["snapshot_generated_at"] is not None
    assert any("adapter:email" in finding for finding in result["simulation"]["world_findings"])
    assert result["proposed_action"] is None
    assert store.list() == []


def test_planner_world_snapshot_is_read_only_and_allows_nonconflicting_state(tmp_path):
    store = ProposedActionStore(str(tmp_path / "actions.db"))
    world = WorldModel(str(tmp_path / "world.db"))
    fact = world.observe(
        subject_id="adapter:notification",
        subject_type="adapter",
        predicate="status",
        value="online",
        confidence=0.93,
        provenance="adapter-health",
    )
    decision = PlannerDecision(
        reply="I prepared the notification for review.",
        action=PlannedAction(
            tool="notification.send",
            description="Notify the owner",
            payload={"message": "Build completed"},
        ),
        provider="test-planner",
    )
    service = PlannerService(store, FixedPlanner(decision), world_model=world)

    result = service.plan("notify the owner")

    assert result["simulation"]["disposition"] == "ready"
    assert result["simulation"]["snapshot_generated_at"] is not None
    assert result["proposed_action"]["status"] == "pending_approval"
    current = world.current("adapter:notification", "status")
    assert len(current) == 1
    assert current[0].id == fact.id
    assert current[0].value == "online"
