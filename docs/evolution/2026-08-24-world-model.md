# Vayu Cognitive Evolution Evidence — 2026-08-24

## Domain
World model.

## Hypothesis
Perception and attention now produce bounded evidence, but Vayu lacks a durable representation of entities, relationships and changing state. Adding an evidence-aware temporal world model is the highest-leverage prerequisite for reliable grounding, contradiction handling and later long-horizon planning.

## Baseline
World-model capability: 0.18. Evidence: no unified entity/state graph.

Known-good rollback point: `38abd21b2de6c7308f0874601066d10aa1bcc9e2`.

## Implementation
- Added `app/world_model.py` with SQLite-backed entities and temporal facts.
- Facts include subject/type, predicate, value, optional object relationship, confidence, provenance, observed time, validity interval and supersession link.
- Stronger contradictory evidence supersedes the current belief while preserving history.
- Lower/equal-confidence contradictory evidence is preserved as historical evidence but cannot displace the stronger current belief.
- Repeated matching evidence can strengthen confidence/provenance without duplicating the fact.
- Entity identity has a stable type; contradictory type reuse fails closed.
- Inputs and query sizes are bounded and observation timestamps must be timezone-aware.

## Safety and authority
The World Model has no executor, planner, network, permission, action-store or approval capability. Stored knowledge cannot itself authorize an external action. Existing approval, expiry, payload-policy and idempotency boundaries are untouched.

## Verification target
Regression coverage must demonstrate persistence, typed relationships, strong/weak contradiction behavior, confidence strengthening and malformed/ambiguous evidence rejection. Full repository CI must remain green before merge.

## Evidence-backed score
If the new tests and full CI pass, world-model capability moves conservatively from 0.18 to 0.36. This does not claim semantic entity extraction, automatic grounding from perception, graph inference, decay, or live environmental awareness.

## Lesson
A useful cognitive world model must preserve uncertainty and history instead of overwriting reality with the most recent statement. Confidence and provenance are part of state, not metadata to add later.

## Next target
Perception is expected to become the weakest measured domain at 0.32. The highest-leverage next increment is a controlled grounding bridge that converts selected attended observations into candidate world facts with explicit provenance/confidence, without allowing sensor content to create action authority.
