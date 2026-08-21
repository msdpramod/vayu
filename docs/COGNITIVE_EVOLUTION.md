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

This attention layer is intentionally built before multimodal perception integration. Adding voice, vision, browser and device streams without a focus-selection boundary would let noisy inputs compete directly with planning and user intent.

## Current evidence snapshot

The attention capability baseline moves conservatively from `0.20` to `0.38` because a tested salience/interruption controller now exists. The score remains well below the target because it is not yet wired into the live command/perception loop and has no durable attentional context. Perception remains the weakest measured domain at `0.15` and is the next likely target.

## Long-term direction

The target is a cognitive operating system with cooperating subsystems analogous to human executive function, memory, attention, perception, action selection, learning and reflection. Base LLMs are reasoning components inside Vayu, not Vayu itself.
