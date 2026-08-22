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

`app/attention.py` is the first dedicated cognitive-control subsystem. It accepts bounded `AttentionStimulus` objects and deterministically ranks them using importance, urgency, novelty and confidence. It can recommend whether a stimulus should interrupt the current focus, but it cannot execute actions, call models, access networks or modify durable state.

Design constraints:

- at most 64 stimuli per ranking batch;
- caller scores are validated to `[0, 1]`;
- duplicate stimulus IDs are rejected;
- deterministic ordering prevents unstable focus oscillation on ties;
- urgency and importance dominate novelty;
- confidence limits uncertain novelty from hijacking focus;
- safety signals receive only a bounded evidence-weighted boost, never an automatic maximum score;
- a safety interruption override requires both high urgency and high confidence;
- ordinary interruptions must clear both an absolute threshold and a margin over current focus.

## Perception subsystem

`app/perception.py` adds Vayu's first Perception Cortex boundary. It normalizes evidence from user text, voice, vision, browser, device and file modalities into bounded attention stimuli. Perception is deliberately an evidence-only layer: it has no planner, executor, action-store, permission, model or network capability.

Design constraints:

- observations require unique bounded IDs, bounded source names and summaries, and timezone-aware timestamps;
- importance, urgency, novelty and confidence are validated to `[0, 1]`;
- batches are capped at 64 observations;
- observations more than 60 seconds in the future fail closed to contain clock-skew/spoofing errors;
- voice and user-text observations become ordinary user-attention stimuli, never privileged safety overrides;
- all modalities converge through the same attention controller, preventing individual adapters from inventing their own action authority;
- real microphone, camera, browser and device adapters remain outside this boundary and must be integrated separately with explicit permissions.

This is intentionally a normalized sensory bus, not a sensor implementation. Vayu can now reason about evidence from multiple modalities through one contract without coupling cognitive control to any particular microphone, camera, browser or operating-system provider.

## Current evidence snapshot

Attention moves conservatively from `0.38` to `0.42` because normalized multimodal evidence now reaches the tested attention boundary. Perception moves from `0.15` to `0.32` because a bounded multimodal normalization layer and failure-path tests now exist. Neither score claims live sensory understanding: microphone, vision-model, browser and device adapters are not yet connected.

The lowest demonstrated capability is now the world model at `0.18`. That is the next high-leverage target because perception and attention need a durable representation of entities, relationships, facts, observations and current state before long-horizon executive planning can become reliable.

## Long-term direction

The target is a cognitive operating system with cooperating subsystems analogous to human executive function, memory, attention, perception, action selection, learning and reflection. Base LLMs are reasoning components inside Vayu, not Vayu itself.
