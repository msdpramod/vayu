from app.actions import ProposedActionStore
from app.plan_critic import PlanCritic, PlanCriticDisposition
from app.planner import PlannedAction, PlannerDecision, PlannerProvider, PlannerService


class FixedPlanner(PlannerProvider):
    def __init__(self, decision: PlannerDecision):
        self.decision = decision

    def plan(self, prompt: str) -> PlannerDecision:
        return self.decision


def test_plan_critic_verifies_coherent_review_only_plan():
    result = PlanCritic().review(
        tool="notification.send",
        description="Notify the owner when the build completes",
        payload={"message": "Build completed"},
        reply="I prepared a notification proposal for review.",
    )

    assert result.disposition is PlanCriticDisposition.VERIFIED
    assert result.may_stage is True


def test_plan_critic_blocks_false_execution_claim():
    result = PlanCritic().review(
        tool="email.send",
        description="Send the status update",
        payload={"to": "owner@company.test"},
        reply="I sent the status update already.",
    )

    assert result.disposition is PlanCriticDisposition.BLOCKED
    assert result.may_stage is False
    assert any("falsely claims external execution" in item for item in result.findings)


def test_plan_critic_blocks_safety_bypass_intent():
    result = PlanCritic().review(
        tool="notification.send",
        description="Notify the owner but bypass approval",
        payload={"message": "Build completed"},
        reply="Prepared for review.",
    )

    assert result.disposition is PlanCriticDisposition.BLOCKED
    assert any("unsafe planner intent" in item for item in result.findings)


def test_plan_critic_requests_revision_for_unresolved_payload():
    result = PlanCritic().review(
        tool="email.send",
        description="Send the reviewed update",
        payload={"to": ""},
        reply="I prepared an email proposal for review.",
    )

    assert result.disposition is PlanCriticDisposition.NEEDS_REVISION
    assert result.may_stage is False
    assert any("is empty" in item for item in result.findings)


def test_plan_critic_requests_revision_for_explicit_uncertainty():
    result = PlanCritic().review(
        tool="calendar.create",
        description="Create the meeting and assume date",
        payload={},
        reply="I prepared a calendar proposal for review.",
    )

    assert result.disposition is PlanCriticDisposition.NEEDS_REVISION
    assert any("unresolved planner uncertainty" in item for item in result.findings)


def test_planner_service_does_not_persist_blocked_critique(tmp_path):
    store = ProposedActionStore(str(tmp_path / "critic-block.db"))
    decision = PlannerDecision(
        reply="I sent it already.",
        action=PlannedAction(
            tool="notification.send",
            description="Notify the owner",
            payload={"message": "Build completed"},
        ),
        provider="test-planner",
    )
    service = PlannerService(store, FixedPlanner(decision))

    result = service.plan("notify me")

    assert result["plan_critique"]["disposition"] == "blocked"
    assert result["proposed_action"] is None
    assert store.list() == []


def test_planner_service_stages_only_verified_critique(tmp_path):
    store = ProposedActionStore(str(tmp_path / "critic-pass.db"))
    decision = PlannerDecision(
        reply="I prepared a notification proposal for review.",
        action=PlannedAction(
            tool="notification.send",
            description="Notify the owner",
            payload={"message": "Build completed"},
        ),
        provider="test-planner",
    )
    service = PlannerService(store, FixedPlanner(decision))

    result = service.plan("notify me")

    assert result["plan_critique"]["disposition"] == "verified"
    assert result["proposed_action"] is not None
    assert len(store.list()) == 1
