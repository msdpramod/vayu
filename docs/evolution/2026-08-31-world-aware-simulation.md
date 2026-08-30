# Vayu cognitive evolution — 2026-08-31

## Domain

Reasoning / World Model integration: prospective simulation against bounded current-world evidence.

## Observation

The v2026.08.30 simulator could model generic prerequisites, expected changes, failure modes and rollback properties, but it had no read-only access to Vayu's present beliefs. A proposal could therefore be marked simulation-ready even when the World Model already contained strong evidence that a required adapter was unavailable.

## Hypothesis

If simulation consumes an immutable, bounded snapshot of only the world subjects relevant to the proposed tool, Vayu can reject known precondition conflicts before human approval without granting the simulator persistence, tool, network, approval or execution authority.

## Implementation

- Added `WorldSnapshot`, an immutable bounded container of current `WorldFact` values.
- Added `WorldModel.snapshot()` with a hard 16-subject cap and the existing 100-fact query cap. Historical/superseded facts are excluded.
- Added explicit simulator world subjects for the allow-listed email, calendar and notification adapters.
- Added high-confidence conflict detection for current adapter `status`/`availability` facts with negative values (`offline`, `unavailable`, `disabled`, `down`).
- A contradiction at confidence >= 0.70 produces `needs_revision` and prevents proposal persistence.
- Lower-confidence negative evidence is surfaced in `world_findings` but does not become a hard fact or block staging.
- Planner simulation now optionally receives a World Model; the production planner receives one, while tests/providers can still run independently without it.
- Simulation responses expose the snapshot timestamp and world findings for observability.

## Safety / authority analysis

This evolution does not expand Vayu's external authority. The World Model is read-only from the simulator path. The simulator still cannot call tools, models, networks, permissions, approvals, executors or external services. It cannot mutate the World Model. A `ready` result still means only that the proposal may enter the existing human approval queue.

Existing safety properties remain mandatory: tool allow-listing, payload policy, confirmation risk, approval expiry, action idempotency and atomic execution ownership.

## Regression evidence

New tests cover:

- immutable snapshots containing only current selected-subject facts;
- hard snapshot subject bounds;
- a high-confidence known-offline email adapter preventing staging;
- low-confidence negative world evidence remaining non-authoritative;
- planner-level prevention of persistence when world state breaks a precondition;
- non-conflicting world snapshots leaving the World Model unchanged while normal pending approval still works.

## Evidence score change

- Reasoning: **0.58 -> 0.61**. Justification: the simulator now checks current-world evidence rather than only static tool profiles. This is still not multi-step causal simulation or probabilistic forecasting.
- World Model: **0.40 -> 0.43**. Justification: durable beliefs can now be exposed through a bounded immutable cognition contract. This is not a full predictive world model.

No other score changed.

## Rollback point

Known-good pre-evolution main: `1565450add49379fc11d73ca6dcca016714e4d87`.

## Lesson

Prospective reasoning needs a distinction between generic possibility and current feasibility. A plan can be structurally valid yet contradict what Vayu already knows. World knowledge should constrain thought through bounded evidence, not by giving reasoning code permission to mutate reality.

## Next proposed target

Add a side-effect-free **counterfactual state delta** layer: construct a temporary predicted world from the current snapshot plus the action's modeled effects, then detect conflicts and invariants before approval. The predicted world must remain ephemeral and must never be written into the durable World Model as if the action actually happened.
