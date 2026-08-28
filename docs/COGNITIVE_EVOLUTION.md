# Vayu Cognitive Evolution

Vayu evolves as a cognitive system rather than by blindly modifying itself.

## Cognitive domains

- Executive control: goals, planning, prioritization, inhibition
- Memory: working, episodic, semantic, procedural and consolidation layers
- Reasoning: planning, critique, verification and simulation
- Attention: salience, interruption handling and focus allocation
- World model: durable entities, relationships, environment and current state
- Skills: explicit tools with measured reliability, latency and cost
- Safety: least privilege, approval boundaries and fail-closed execution
- Perception: voice, vision, files, browser and device signals

## Evolution loop

1. Observe measurable capability signals.
2. Score each cognitive domain conservatively.
3. Select the largest demonstrated gap or a prerequisite that unlocks it.
4. Produce an evolution proposal/hypothesis.
5. Require review before architectural or permission-changing work.
6. Implement through normal tested Git changes.
7. Measure results and update evidence.
8. Consolidate lessons into future design decisions.

The evolution engine is proposal-only. It cannot modify source code, permissions, tools, prompts, models, configuration or external systems. Vayu may improve continuously, but no self-improvement mechanism bypasses the existing human-approval and execution boundaries.

## Attention subsystem

`app/attention.py` provides deterministic cognitive focus control. It accepts bounded `AttentionStimulus` objects and ranks them using importance, urgency, novelty and confidence. It can recommend whether a stimulus should interrupt current focus, but it cannot execute actions, call models, access networks or modify durable state.

Key constraints include bounded batches, validated scores, duplicate rejection, deterministic ordering, confidence-limited novelty, bounded safety boosts, and interruption thresholds that must exceed both an absolute floor and the current focus by a margin.

## Perception subsystem

`app/perception.py` is Vayu's normalized sensory boundary. Evidence from user text, voice, vision, browser, device and file modalities becomes attention stimuli through one bounded contract. Perception remains evidence-only and has no planner, executor, action-store, permission, model or network capability.

`app/grounding.py` then connects attended evidence to the durable World Model. Grounding binds observation identity to the attention decision, applies a salience threshold, caps confidence by source evidence and preserves modality/source provenance. Raw perception therefore cannot write arbitrary durable beliefs directly.

## Deterministic semantic extractor

`app/semantic_extractor.py` provides a known-precision baseline before probabilistic extraction is introduced. It currently recognizes only exact, complete sentence shapes for device service status, browser page state and file lifecycle evidence. It rejects extra or ambiguous text, unsupported modalities, duplicate IDs and oversized batches.

The extractor copies source confidence rather than increasing it and produces only a `SemanticFrame`. That frame still has to pass the semantic boundary and independent critic. This gives future LLM-backed extraction a measurable contract to outperform without weakening trust boundaries.

## Semantic understanding boundary

`app/semantics.py` adds a cognition-only semantic verification stage before grounding. A provider may propose a `SemanticFrame`, but Vayu accepts it only when it passes an explicit versioned schema.

Current schemas cover a deliberately narrow set of structured meanings:

- `device.service_status.v1`
- `browser.page_state.v1`
- `file.lifecycle.v1`

The semantic boundary requires:

- exact observation/attention/frame identity binding;
- modality/schema agreement;
- allow-listed predicates and, where defined, allow-listed values;
- an evidence span that must actually occur in the source observation summary;
- minimum attention salience and effective evidence confidence;
- confidence capped to `min(observation confidence, frame confidence)`;
- bounded subject/evidence fields, bounded batches and duplicate rejection;
- consistent object relationship shape when an object entity is proposed.

Failure produces abstention rather than a guessed fact. The boundary has no model, network, planner, executor, persistence, action-store, permission or approval authority. Future LLM-backed extractors must feed this boundary rather than writing directly to the World Model.

## Semantic critic / verifier

`app/critic.py` adds an independent second-pass critic after semantic admission and before durable grounding. Passing a schema is therefore no longer sufficient by itself: the claim must also survive source-confidence and existing-world-context checks.

The critic:

- requires exact observation/result/candidate identity binding;
- rejects any confidence escalation beyond the original sensory evidence;
- examines only bounded current World Model context;
- ignores historical contradictions that are no longer current;
- abstains when substantially stronger contradictory evidence already exists;
- returns an explicit `conflict` disposition when competing beliefs are close enough that silent overwrite would be unsafe;
- never boosts semantic confidence merely because a matching current fact exists.

The semantic critic is cognition-only and has no persistence, model, network, planner, executor, permission, approval, or action authority. A conflict is information for later reasoning, not permission to act.

## Planner critic / metacognition

`app/plan_critic.py` adds a deterministic second-pass reasoning boundary after the planner's structural/tool/payload validation and before a proposal can enter the durable human approval queue.

The planner critic returns one of three dispositions:

- `verified` — no deterministic objection was found and the plan may continue to normal pending approval;
- `needs_revision` — unresolved payload fields or explicit uncertainty remain, so nothing is persisted;
- `blocked` — the planner claims an external action already happened or expresses an intent to bypass safety/approval, so nothing is persisted.

The critic also bounds description/reply sizes and top-level payload shape. It does not rewrite plans, approve actions, persist state, call a model, access the network, invoke tools, or execute side effects. A verified critique is not execution permission; it only means the proposal may reach the existing `pending_approval` state.

This establishes the first planning metacognition loop:

`Planner -> structural/payload validation -> Plan Critic -> human approval queue`

The next reasoning layer should be a bounded simulator that predicts preconditions, expected state transitions, failure modes and rollback requirements without executing the proposed action.

## World Model

`app/world_model.py` stores durable typed entities and temporal facts with confidence and provenance. Stronger contradictory evidence can supersede a current belief while preserving history; weaker contradictory evidence is retained without displacing the stronger current state. This subsystem is also cognition-only.

## Current evidence snapshot

- Safety: `0.88` — time-bounded approval lifecycle and fail-closed execution.
- Memory: `0.55` — durable SQLite memory exists; consolidation and semantic recall remain limited.
- Reasoning: `0.54` — structured planning now has an independent deterministic plan critic before staging, while causal simulation, multi-step verification and broader metacognition remain limited.
- Skills: `0.52` — explicit registry exists; learned reliability/latency/cost scoring is absent.
- Perception: `0.44` — exact deterministic extraction covers narrow device/browser/file observations before semantic validation and critique; live adapters and general extraction are absent.
- Executive: `0.42` — orchestration exists; hierarchical goals and long-horizon control remain limited.
- Attention: `0.42` — bounded salience control consumes normalized perception but lacks durable attentional context.
- World model: `0.40` — durable evidence-aware state graph with grounding and contradiction handling.

The scores are evidence labels, not claims of human-level capability. They should only move when tests or observable behavior justify the change.

## Next scientific direction

Add bounded pre-execution simulation after the plan critic and before human approval: `Planner -> Plan Critic -> Simulation -> Approval Queue`.

The first simulator should remain cognition-only and deterministic. It should model expected state changes, prerequisites, likely failure modes, reversibility/rollback requirements and uncertainty for allow-listed tools without calling the tool itself. Simulation failure or missing rollback information should prevent the plan from reaching approval rather than silently degrading safety.

LLM-backed semantic extraction can follow the deterministic baseline, but it must use the same schema boundary and critic rather than gaining direct World Model access. Live microphone/camera integration should remain downstream of these cognitive trust boundaries.

## Long-term direction

The target is a cognitive operating system with cooperating subsystems analogous to human executive function, memory, attention, perception, action selection, learning and reflection. Base LLMs are reasoning components inside Vayu, not Vayu itself.
