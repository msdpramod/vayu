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
  -> Ephemeral Counterfactual Futures
  -> Human Approval Queue
  -> independently gated executor
```

Cognitive output never implies execution authority.

## Attention and perception

`app/attention.py` provides deterministic focus control over bounded stimuli using importance, urgency, novelty and confidence. `app/perception.py` normalizes user text, voice, vision, browser, device and file observations into the attention boundary.

`app/semantic_extractor.py`, `app/semantics.py`, `app/critic.py` and `app/grounding.py` provide a conservative semantic path: exact deterministic extraction where supported, explicit schemas, evidence anchoring, confidence caps, abstention, contradiction review and provenance-preserving grounding. Future probabilistic/LLM extraction must use the same trust boundaries.

## World Model

`app/world_model.py` stores durable typed entities and temporal facts with confidence and provenance. Stronger contradictory evidence can supersede a current belief while preserving history; weaker contradictory evidence is retained without displacing the stronger current state.

The World Model exposes `WorldSnapshot`, an immutable bounded view of current facts for selected subjects. Snapshot queries are capped to 16 subjects and the existing 100-fact query limit, and historical/superseded facts are excluded. Cognition-only consumers can therefore reason about current beliefs without receiving mutation authority.

Counterfactual reasoning is intentionally separated from this durable state. Predicted future deltas are temporary cognitive objects and are never persisted as observations merely because Vayu simulated them.

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

Simulation does not call tools, models, networks, permissions, approval systems, executors or external services, and it cannot mutate the World Model. `ready` means only that a proposal is coherent enough for the next cognitive gate.

## Ephemeral counterfactual futures

`app/counterfactual.py` projects a `ready` simulation into a bounded set of mutually exclusive future-state deltas. The first version deliberately uses three branches for each allow-listed external action:

- `success` — the expected external effect may have occurred;
- `failure` — the external effect did not occur;
- `ambiguous` — the provider outcome is unknown and reconciliation is required before retry.

The branch limit is three and payloads remain bounded to 64 top-level keys. Predicted facts carry conservative confidence labels but no invented outcome probabilities; the result explicitly states that outcome probabilities are unknown.

Counterfactual facts are not `WorldFact` observations. They have no persistence path and never update current durable state. A counterfactual result must be `ready` before a planner-created action may enter the existing human approval queue.

## Current evidence snapshot

- Safety: `0.88` — time-bounded approval lifecycle and fail-closed execution.
- Reasoning: `0.64` — independent plan critique, current-world simulation, and bounded success/failure/ambiguous counterfactual futures; multi-step causal search and alternative-plan comparison remain limited.
- Memory: `0.55` — durable SQLite memory exists; consolidation and semantic recall remain limited.
- Skills: `0.52` — explicit registry exists; learned reliability/latency/cost scoring is absent.
- World model: `0.45` — durable evidence-aware state graph plus immutable current snapshots and separate non-persistent predicted deltas; learned predictive transitions remain limited.
- Perception: `0.44` — exact deterministic extraction covers narrow device/browser/file observations; live adapters and general extraction are absent.
- Executive: `0.42` — orchestration exists; hierarchical goals and long-horizon control remain limited.
- Attention: `0.42` — bounded salience control consumes normalized perception but lacks durable attentional context.

These scores are evidence labels, not claims of human-level capability. They move only when observable behavior and tests justify the change.

## Safety invariants

Vayu preserves explicit tools/skills, least privilege, payload policy, permission checks, human approval for consequential external actions, approval expiry, idempotency, atomic execution ownership and fail-closed behavior. There is no unrestricted shell execution and no unrestricted self-modification.

KUPPA AI remains independently runnable and human-facing: KUPPA is the heart/personality/presence layer; Vayu is the brain/cognitive engine. Reuse occurs through architectural patterns and versioned contracts, not brittle cross-repository runtime coupling.

## Next scientific direction

Add **bounded alternative-plan comparison and counterfactual invariant checking** over the same immutable current-world snapshot:

```text
Current World Snapshot
  + Candidate Plan A -> Counterfactual Futures A
  + Candidate Plan B -> Counterfactual Futures B
  -> Compare prerequisites / ambiguity / reversibility / risk / expected effects
  -> Human review
```

The comparison layer must not silently choose or execute an action. It should expose evidence, assumptions and tradeoffs while preserving uncertainty. Later iterations can add learned transition models, multi-step causal search and uncertainty propagation only after deterministic invariants remain stable.
