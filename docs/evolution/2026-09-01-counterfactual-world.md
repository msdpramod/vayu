# Vayu cognitive evolution — 2026-09-01

## Domain

Reasoning + World Model: ephemeral counterfactual futures.

## Baseline observed

- Previous known-good `main`: `3fb816b67d1a70ad7acc0f380b53bd918f6bcde7` (`v2026.08.31`).
- GitHub Actions CI run 207 completed successfully for that head.
- Current planner pipeline could critique a plan, inspect a bounded immutable World Model snapshot, and simulate prerequisites/consequences before approval.
- Missing capability: simulation described only one proposal abstractly; it did not explicitly represent mutually exclusive future states or distinguish success, failure, and ambiguous external outcomes.

## Hypothesis

If Vayu represents a proposed external action as a bounded set of explicit temporary future-state deltas, then prospective reasoning becomes more faithful to real external systems: success is not assumed, ambiguous provider outcomes remain first-class, and imagined state cannot contaminate durable beliefs.

## Increment

Added `app/counterfactual.py` with a cognition-only `CounterfactualSimulator` and immutable counterfactual data structures.

For the existing allow-listed `email.send`, `calendar.create`, and `notification.send` actions it creates at most three deterministic future branches:

1. `success` — the expected external effect may have occurred;
2. `failure` — the external effect did not occur;
3. `ambiguous` — outcome is unknown and requires reconciliation before retry.

The predicted facts are deltas only. They are not observations, are never written to `WorldModel`, and use conservative confidence labels rather than invented probabilities. The simulator explicitly states that outcome probabilities are unknown.

Planner flow is now:

`Planner -> validation -> Plan Critic -> current-world simulation -> counterfactual futures -> Human Approval Queue`

Only a `ready` counterfactual result may proceed to staging. The new result is exposed in planner output for observability and review.

## Safety / regression impact

- No executor, network, model, permission, secret, approval, or persistence capability was added to the counterfactual layer.
- Human approval remains mandatory.
- Existing tool allow-lists, payload policy, approval expiry, idempotency, atomic execution ownership, and fail-closed execution are unchanged.
- Imagined future facts are structurally separated from durable World Model facts.
- Counterfactual projection refuses to run when the base simulation is not ready or when payload/tool bounds are not satisfied.

## Validation evidence

Added tests for:

- success/failure/ambiguous bounded future branches;
- ambiguous-outcome reconciliation;
- no durable World Model mutation from imagined facts;
- fail-closed behavior when base simulation is not ready;
- explicit refusal to invent outcome probabilities;
- planner integration proving counterfactual analysis happens before pending approval staging.

## Capability evidence

- Reasoning: `0.61 -> 0.64` — justified by explicit bounded alternative-future representation and planner gating. No multi-step causal search, learned transition model, or plan comparison is claimed.
- World Model: `0.43 -> 0.45` — justified by immutable current-state snapshots now supporting separate non-persistent predicted deltas. No predictive durable model is claimed.

## KUPPA pattern reused

The intelligence/authority separation is preserved: Vayu may imagine multiple futures, while KUPPA remains the human-facing heart/presence layer and neither system receives implicit execution authority. No cross-repository runtime dependency was introduced.

## Rollback point

`3fb816b67d1a70ad7acc0f380b53bd918f6bcde7`

## Lesson learned

A useful brain must not confuse an intended action with an accomplished future. External systems can succeed, fail, or enter an ambiguous state, and ambiguity must survive cognition rather than being rounded into certainty.

## Next target

Add **counterfactual invariant/conflict analysis across alternative plans**, initially deterministic and bounded. Vayu should be able to compare two or more safe proposals against the same current snapshot using explicit criteria such as reversibility, unresolved ambiguity, prerequisites, risk, and expected effects—without executing or silently choosing an action.
