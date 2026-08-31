from app.actions import PENDING, ProposedActionStore
from app.counterfactual import (
    CounterfactualDisposition,
    CounterfactualOutcome,
    CounterfactualSimulator,
)
from app.planner import PlannedAction, PlannerDecision, PlannerProvider, PlannerService
from app.simulator import CognitiveSimulator
from app.world_model import WorldModel


class FixedPlanner(PlannerProvider):
    def __init__(self, decision: PlannerDecision):
        self.decision = decision

    def plan(self, prompt: str) -> PlannerDecision:
        return self.decision


def test_counterfactual_projects_bounded_alternative_futures_without_persistence(tmp_path):
    model = WorldModel(str(tmp_path / "world.db"))
    model.observe(
        subject_id="adapter:email",
        subject_type="adapter",
        predicate="status",
        value="available",
        confidence=0.95,
        provenance="health-check",
    )
    simulator = CognitiveSimulator()
    snapshot = model.snapshot(simulator.context_subjects("email.send"))
    simulation = simulator.simulate(
        tool="email.send",
        payload={"to": "owner@example.com"},
        world_snapshot=snapshot,
    )

    future = CounterfactualSimulator().project(
        tool="email.send",
        payload={"to": "owner@example.com"},
        simulation=simulation,
        world_snapshot=snapshot,
    )

    assert future.disposition is CounterfactualDisposition.READY
    assert future.may_stage is True
    assert len(future.branches) == 3
    assert {branch.outcome for branch in future.branches} == {
        CounterfactualOutcome.SUCCESS,
        CounterfactualOutcome.FAILURE,
        CounterfactualOutcome.AMBIGUOUS,
    }
    ambiguous = next(branch for branch in future.branches if branch.outcome is CounterfactualOutcome.AMBIGUOUS)
    assert ambiguous.requires_reconciliation is True
    assert future.base_snapshot_generated_at == snapshot.generated_at
    assert model.current("effect:email.send") == []


def test_counterfactual_refuses_to_project_from_failed_base_simulation():
    simulation = CognitiveSimulator().simulate(
        tool="email.send",
        payload={},
    )

    future = CounterfactualSimulator().project(
        tool="email.send",
        payload={},
        simulation=simulation,
    )

    assert future.disposition is CounterfactualDisposition.BLOCKED
    assert future.may_stage is False
    assert future.branches == ()
    assert "base simulation is not ready" in future.conflicts


def test_counterfactual_does_not_assign_fake_outcome_probabilities():
    simulator = CognitiveSimulator()
    simulation = simulator.simulate(
        tool="notification.send",
        payload={"message": "Build completed"},
    )

    future = CounterfactualSimulator().project(
        tool="notification.send",
        payload={"message": "Build completed"},
        simulation=simulation,
    )

    assert future.disposition is CounterfactualDisposition.READY
    assert any("probabilities are unknown" in assumption for assumption in future.assumptions)
    assert all(
        0.0 < fact.confidence < 1.0
        for branch in future.branches
        for fact in branch.delta
    )


def test_planner_exposes_counterfactual_branches_before_staging(tmp_path):
    store = ProposedActionStore(str(tmp_path / "planner.db"))
    decision = PlannerDecision(
        reply="I prepared an email proposal for review.",
        action=PlannedAction(
            tool="email.send",
            description="Send reviewed status update",
            payload={"to": "owner@example.com"},
        ),
        provider="test-planner",
    )
    service = PlannerService(store, FixedPlanner(decision))

    result = service.plan("send the update")

    assert result["simulation"]["disposition"] == "ready"
    assert result["counterfactual"]["disposition"] == "ready"
    assert {branch["outcome"] for branch in result["counterfactual"]["branches"]} == {
        "success",
        "failure",
        "ambiguous",
    }
    assert result["proposed_action"]["status"] == PENDING
