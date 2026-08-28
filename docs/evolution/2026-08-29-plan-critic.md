# Vayu cognitive evolution — 2026-08-29

## Domain

Reasoning — planner metacognition / independent plan critic.

## Observed state

Main was at `728a56f5eca7d147ba4412494885bac75bebbade` (`v2026.08.28`). Vayu already had structured planner output, strict allow-listed tools, payload policy, mandatory confirmation, semantic critique, approval expiry and fail-closed execution. The remaining reasoning gap was that structurally valid planner output could still reach the human approval queue without an independent second process checking for self-contradiction, false execution claims, explicit safety-bypass intent or unresolved uncertainty.

The measured weakest domain was still World Model at `0.40`, but planner metacognition was selected as the higher-leverage prerequisite because the documented cognitive path explicitly depended on `Planner -> Critic -> Simulation -> Approval Queue`. Building simulation before an independent critic would let bad plans consume simulation/approval attention rather than rejecting them earlier.

## Hypothesis

A cognition-only deterministic plan critic placed after structural/payload validation but before durable staging will reduce unsafe or incoherent plans reaching human approval without increasing action authority. It should make Vayu willing to challenge its own planner output while preserving the existing executor and approval boundaries.

## Implementation

Added `app/plan_critic.py` with:

- explicit `verified`, `needs_revision`, and `blocked` dispositions;
- bounded description/reply/payload surface;
- blocking for false claims that email/calendar/notification side effects already happened;
- blocking for explicit approval/safety-bypass intent and high-risk out-of-scope phrases;
- revision-required results for null/empty payload fields and explicit unresolved uncertainty such as guessed recipients or dates;
- deterministic findings for observability and future simulation input;
- no persistence, model, network, tool, executor, action-store, permission, approval or side-effect authority.

Integrated the critic into `PlannerService.stage_decision()` after existing allow-list/risk/payload validation and before `ProposedActionStore.propose()`. Only `verified` critique results can enter `pending_approval`; `needs_revision` and `blocked` return critique evidence while persisting nothing.

Added regression tests covering a coherent plan, false execution claims, explicit safety bypass, unresolved payload fields, explicit uncertainty, non-persistence of blocked plans, and successful staging of verified plans.

## Validation

The feature-and-test branch CI job completed successfully with the full `python -m pytest -q` step before documentation/version finalization. A final CI run for the complete versioned branch is required before fast-forward publication to `main`.

## Evidence / score

Reasoning moves conservatively from `0.50` to `0.54` because Vayu now has independent deterministic critique of planner output before staging. This does not claim causal simulation, multi-step plan validation, learned metacognition, or general verification of arbitrary reasoning.

No other cognitive score changed.

## Safety / regression impact

The change narrows, rather than expands, the set of planner outputs that can reach approval. Existing tool allow-lists, planner payload policy, mandatory confirmation, human approval, approval expiry, idempotency, atomic execution claim, executor isolation and fail-closed behavior are unchanged.

A `verified` critique is not approval and cannot execute anything.

## KUPPA pattern reused

The useful KUPPA principle remains separation of intelligence from authority: Vayu may reason about and criticize its own proposals, while authority to perform consequential actions remains outside the reasoning system. No runtime dependency on KUPPA AI was introduced.

## Rollback point

`728a56f5eca7d147ba4412494885bac75bebbade`

## Blockers

None in the implementation. Final publication remains gated on the complete branch CI result.

## Lesson

Human-like intelligence is not just generation; it includes inhibition. A planning system becomes more trustworthy when a separate mechanism can say “this is uncertain,” “this contradicts the safety contract,” or “you are claiming an action happened when it did not” before a human is asked to approve anything.

## Next target

Build a bounded cognition-only pre-execution simulator after the plan critic: `Planner -> Plan Critic -> Simulation -> Approval Queue`. It should predict prerequisites, expected state transitions, likely failure modes, reversibility/rollback requirements and uncertainty for allow-listed tools without invoking them. Plans with missing prerequisites or unacceptable irreversible risk should fail closed before approval.
