# Vayu Cognitive Evolution

Vayu evolves as a cognitive operating system rather than by blindly modifying itself. Base LLMs are reasoning components inside Vayu; they are not Vayu itself.

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
4. Form a falsifiable improvement hypothesis.
5. Implement through normal reviewed/tested Git changes.
6. Verify success and a relevant failure path.
7. Compare behavior and record evidence.
8. Consolidate lessons into future design decisions.

The evolution engine is proposal-only. It cannot modify source code, permissions, tools, prompts, models, configuration or external systems. No self-improvement mechanism may bypass the existing human-approval or execution boundaries.

## Current cognition pipeline

```text
Perception
  -> Attention
  -> deterministic/schema-constrained semantic interpretation
  -> Semantic Critic
  -> Grounding
  -> World Model

Planner
  -> structural/tool/payload validation
  -> Plan Critic
  -> World-aware Cognitive Simulation
  -> Human Approval Queue
  -> independently gated executor
```

Cognitive output never implies execution authority.

## Attention and perception

`app/attention.py` provides deterministic focus control over bounded stimuli using importance, urgency, novelty and confidence. `app/perception.py` normalizes user text, voice, vision, browser, device and file observations into the attention boundary.

`app/semantic_extractor.py`, `app/semantics.py`, `app/critic.py` and `app/grounding.py` provide a conservative semantic path: exact deterministic extraction where supported, explicit schemas, evidence anchoring, confidence caps, abstention, contradiction review and provenance-preserving grounding. Future probabilistic/LLM extraction must use the same trust boundaries.

## World Model

`app/world_model.py` stores durable typed entities and temporal facts with confidence and provenance. Stronger contradictory evidence can supersede a current belief while preserving history; weaker contradictory evidence is retained without displacing the stronger current state.

The World Model now also exposes `WorldSnapshot`, an immutable bounded view of current facts for selected subjects. Snapshot queries are capped to 16 subjects and the existing 100-fact query limit, and historical/superseded facts are excluded. Cognition-only consumers can therefore reason about current beliefs without receiving mutation authority.

## Planner metacognition

`app/plan_critic.py` independently reviews structurally valid plans before simulation. It can return `verified`, `needs_revision`, or `blocked`; unresolved payload fields, explicit uncertainty, claims that side effects already happened, and approval-bypass language stop the plan before persistence.

## World-aware cognitive simulation

`app/simulator.py` is a deterministic, side-effect-free prospective reasoning boundary for the explicitly allow-listed `email.send`, `calendar.create`, and `notification.send` tools.

It models:

- required payload fields and execution prerequisites;
- expected external state changes;
- likely failure modes;
- reversibility and rollback/compensation;
- relevant current World Model state through an immutable snapshot.

Each tool maps to an explicit adapter-world subject (`adapter:email`, `adapter:calendar`, `adapter:notification`). If the current snapshot contains high-confidence (`>= 0.70`) evidence that the adapter is `offline`, `unavailable`, `disabled`, or `down`, simulation returns `needs_revision` and the proposal never reaches human approval. Lower-confidence contradictory evidence is surfaced but is not promoted into a hard fact.

Simulation does not call tools, models, networks, permissions, approval systems, executors or external services, and it cannot mutate the World Model. `ready` means only that a proposal is coherent enough to enter the existing approval queue.

## Current evidence snapshot

- Safety: `0.88` — time-bounded approval lifecycle and fail-closed execution.
- Reasoning: `0.61` — independent plan critique plus deterministic consequence simulation constrained by bounded current-world evidence; multi-step causal counterfactual reasoning remains limited.
- Memory: `0.55` — durable SQLite memory exists; consolidation and semantic recall remain limited.
- Skills: `0.52` — explicit registry exists; learned reliability/latency/cost scoring is absent.
- Perception: `0.44` — exact deterministic extraction covers narrow device/browser/file observations; live adapters and general extraction are absent.
- World model: `0.43` — durable evidence-aware state graph plus bounded immutable current-state snapshots; predictive transitions remain limited.
- Executive: `0.42` — orchestration exists; hierarchical goals and long-horizon control remain limited.
- Attention: `0.42` — bounded salience control consumes normalized perception but lacks durable attentional context.

These scores are evidence labels, not claims of human-level capability. They move only when observable behavior and tests justify the change.

## Safety invariants

Vayu preserves explicit tools/skills, least privilege, payload policy, permission checks, human approval for consequential external actions, approval expiry, idempotency, atomic execution ownership and fail-closed behavior. There is no unrestricted shell execution and no unrestricted self-modification.

KUPPA AI remains independently runnable and human-facing: KUPPA is the heart/personality/presence layer; Vayu is the brain/cognitive engine. Reuse occurs through architectural patterns and versioned contracts, not brittle cross-repository runtime coupling.

## Next scientific direction

Add an **ephemeral counterfactual state delta** after current-world precondition checking:

```text
Current World Snapshot
  + Proposed Action Effects
  -> Temporary Predicted World
  -> Conflict / Invariant Analysis
  -> Approval Queue
```

The predicted world must never be persisted as if an action actually happened. The first version should remain deterministic, bounded and explicit about assumptions. Later iterations can add multi-step causal simulation, uncertainty propagation and alternative-plan comparison while keeping action authority outside cognition.
