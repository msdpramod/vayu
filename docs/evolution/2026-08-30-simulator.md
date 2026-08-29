# Vayu Cognitive Evolution — 2026-08-30

## Domain

Reasoning / pre-execution simulation.

## Observation and gap

The v2026.08.29 planner path had two independent protections before human approval: structural/payload validation and a deterministic plan critic. The critic could reject unsafe intent, false execution claims, explicit uncertainty and unresolved fields, but it did not model what an otherwise coherent action would require or what could happen if it were eventually approved.

Current evidence therefore justified Reasoning at 0.54, with bounded consequence simulation explicitly identified as the next dependency before broader executive planning.

## Hypothesis

If every critic-verified proposal is passed through a deterministic, side-effect-free simulation profile before persistence, Vayu can reason about prerequisites, expected state changes, likely failure modes, reversibility and rollback without increasing its authority. Incomplete or unsupported simulations should fail closed and never enter the approval queue.

## Implementation

Added `app/simulator.py` with explicit simulation profiles for the only planner-proposable tools:

- `notification.send`
- `email.send`
- `calendar.create`

Each profile describes bounded preconditions, expected external state changes, likely failure modes, rollback/compensation guidance and whether the action is meaningfully reversible. Tool-specific required fields are checked without calling the tool or any external provider.

The planner pipeline is now:

`Planner -> structural/payload validation -> Plan Critic -> Cognitive Simulation -> pending_approval`

Only a simulation disposition of `ready` may be persisted. `needs_revision` and `blocked` results are returned as cognitive evidence and produce no proposed action.

The local deterministic planner remains useful as an offline analysis fallback, but its intentionally payload-free proposal syntax no longer stages incomplete external actions. It now reaches the simulator, receives `needs_revision`, and stops before persistence.

## Safety and authority

The simulator has no executor, action-store, model, network, filesystem, permission, approval or secret capability. It receives only an already validated tool name and payload and returns immutable cognitive analysis.

A successful simulation is not approval and is not execution permission. Existing human approval, approval expiry, payload policy, idempotency and atomic execution ownership remain unchanged.

Unknown tools have no simulation profile and fail closed. This preserves the principle that intelligence may predict consequences but cannot manufacture authority.

## Validation added

Regression coverage verifies:

- a complete notification proposal receives a bounded simulation and may proceed to normal pending approval;
- an email without an explicit recipient receives `needs_revision` and is not staged;
- a calendar proposal without an explicit start receives `needs_revision`;
- an unknown tool is blocked by the simulator itself when tested in isolation;
- oversized simulation text is rejected;
- Ollama-backed proposals still cannot execute and now expose simulation evidence;
- the local/API fallback no longer persists incomplete payload-free proposals.

The branch must pass the repository's GitHub Actions pytest workflow before merge. Local clone-based pytest was unavailable in this runtime because DNS resolution for `github.com` failed, so GitHub Actions is the authoritative regression gate for this run.

## Evidence score

Reasoning: **0.54 -> 0.58**.

The increase is intentionally limited. Vayu can now deterministically model one-step consequences for three allow-listed actions, but it does not yet perform causal multi-step simulation, probabilistic outcome estimation, resource/cost forecasting, or world-model-based counterfactual reasoning.

No other cognitive domain score was increased.

## KUPPA pattern reused

The existing KUPPA-inspired separation remains: Vayu may reason more deeply about an action, while authority is still supplied by independent human approval. No KUPPA runtime dependency was introduced.

## Rollback point

Known-good main before this evolution: `261f9f9a1cf9431bce4a14e3eecbc1096b1c5c9f` (`v2026.08.29`, CI run #182 successful).

## Lesson

A plan that is syntactically valid and critic-approved is still not necessarily executable or safe to retry. Human-like executive reasoning needs an explicit model of prerequisites, consequences, ambiguous failures and compensation before action selection.

## Next target

The weakest measured domain after this increment remains the World Model at 0.40, closely followed by Executive and Attention at 0.42. The highest-leverage next step is to connect simulation to a **read-only World Model snapshot** so Vayu can verify preconditions against known current state and produce bounded counterfactual state deltas without mutating reality. That should precede multi-step/hierarchical planning.
