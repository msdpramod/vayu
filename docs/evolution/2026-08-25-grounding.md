# 2026-08-25 — Attention-gated cognitive grounding

## Observed gap

Vayu had three independent pieces: normalized perception evidence, deterministic attention selection, and a durable evidence-aware World Model. They were not connected. A sensory observation could become salient, but there was no controlled path for selected evidence to become structured durable knowledge.

## Hypothesis

A narrow grounding boundary that binds one structured knowledge candidate to one perception observation and its attention decision will improve perception/world-model integration without giving sensors, extractors, LLMs, or attention any action authority.

## Design

Added `CognitiveGroundingGateway` and `GroundingCandidate` in `app/grounding.py`.

The gateway:

- requires the observation ID, attention stimulus ID, and grounding candidate ID to match;
- refuses grounding below a configurable salience threshold;
- caps persisted confidence to `min(observation confidence, candidate confidence)` so extractors cannot manufacture stronger certainty than source evidence;
- builds provenance from modality, source, and observation identity;
- writes only through the existing `WorldModel.observe` evidence/contradiction policy;
- bounds grounding batches to 32 candidates and rejects duplicate observation IDs;
- contains no planner, executor, action-store, permission, network, model, tool, or approval capability.

The first implementation deliberately does not parse arbitrary natural language. A semantic extractor must produce an explicit typed candidate in a future evolution and will remain downstream of perception/attention safety boundaries.

## Verification target

Regression tests cover:

1. attended evidence persists with provenance and confidence capped by the sensory source;
2. low-salience evidence is not persisted;
3. cross-observation candidate binding fails closed;
4. grounding batches reject duplicates and excessive size.

## Capability evidence

- Perception: `0.32 -> 0.36`. Evidence: normalized observations can now participate in a tested Perception -> Attention -> World Model path. No live sensor or semantic-understanding claim is made.
- World model: `0.36 -> 0.40`. Evidence: the durable graph now receives attention-gated sensory provenance and source-bounded confidence. Semantic grounding is still explicit/manual.
- Attention: remains `0.42`; this change consumes attention output but does not materially increase the attention controller itself.
- Safety: unchanged; cognition-only grounding creates no external side-effect authority.

## Regression gate

Expected invariants: existing action approval, expiry, payload policy, idempotency, executor isolation, perception bounds, attention bounds, and World Model contradiction behavior remain unchanged.

## KUPPA pattern reused

The useful pattern is separation of human-facing observation/context from authority: KUPPA-style context may provide evidence, while Vayu independently decides what is cognitively salient and stores only bounded provenance-aware knowledge. No runtime dependency on KUPPA AI is introduced.

## Rollback point

`0714fef0c417ee13d48568c7839b52dda104ae0e`

## Lesson

A cognitive system should not let raw perception write directly into beliefs. Attention and evidence confidence must constrain what enters the world model, and provenance must survive the transition.

## Next proposed target

Perception remains the weakest measured domain at `0.36`. The next useful step is a deterministic, schema-constrained semantic extraction boundary for selected observations (starting with structured device/browser/file events), with abstention and uncertainty rather than free-form LLM belief insertion. Live microphone/camera adapters should come only after that semantic boundary is testable.
