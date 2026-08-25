# 2026-08-26 — Schema-constrained semantic understanding

## Observed gap

Vayu could normalize perception, select salient observations, and ground explicit structured candidates into the World Model. The missing boundary was semantic verification: a future extractor or LLM could propose a structured candidate, but there was no dedicated schema layer to constrain what meanings were admissible or require claims to be visibly anchored to source evidence.

The previous evolution explicitly identified this as the next high-leverage Perception target. Current CI for `dbfcb1dc` was green before this change.

## Hypothesis

A provider-independent semantic boundary that validates versioned schemas, source-evidence anchors, modality, confidence and salience before producing a `GroundingCandidate` will improve Vayu's ability to turn sensory evidence into meaning while reducing hallucinated or tool-smuggled beliefs.

## Design

Added `app/semantics.py` with:

- `SemanticSchema`: versioned allow-listed semantic contracts;
- `SemanticFrame`: provider-proposed meaning bound to one observation;
- `SemanticResult`: accepted/abstained result with an optional grounding candidate;
- `SemanticUnderstandingBoundary`: cognition-only validation and abstention.

Initial schemas are deliberately narrow: device service status, browser page state, and file lifecycle state. The boundary requires exact observation/attention/frame identity, matching modality, allow-listed predicates and values, a literal source evidence span, minimum salience, and minimum effective confidence. Accepted confidence is capped to the weaker of source observation and semantic frame confidence.

The layer has no model, network, planner, executor, action store, persistence, permission or approval capability. A future LLM may propose frames, but it cannot bypass this boundary or write directly to the World Model.

## Verification target

Regression coverage verifies:

1. valid source-anchored semantics produce a typed grounding candidate with confidence capped by source evidence;
2. claims without a source evidence span abstain;
3. predicates and values outside the schema abstain;
4. low-confidence and low-salience claims abstain;
5. cross-observation binding fails closed;
6. a schema cannot be used for the wrong modality;
7. semantic batches are bounded and reject duplicate observations;
8. duplicate schema names are rejected.

## Capability evidence

- Perception: `0.36 -> 0.40`. Evidence: attended observations can now pass through an explicit semantic verification/abstention stage before grounding. This does not claim automatic natural-language extraction, microphone/camera understanding, or general semantic comprehension.
- World model: remains `0.40`; this change protects its input boundary but does not materially extend graph capability.
- Attention: remains `0.42`; this change consumes salience rather than improving attention policy.
- Reasoning: remains `0.48`; no critic/verifier reasoning loop is added yet.
- Safety: unchanged at `0.88`; the semantic layer creates no action authority.

## Regression gate

Existing invariants must remain unchanged: action approval and expiry, payload policy, idempotency, executor isolation, perception bounds, attention bounds, grounding confidence caps, World Model provenance and contradiction behavior.

## KUPPA pattern reused

The reused architectural idea is separation between rich human-facing interpretation and execution authority. KUPPA-style conversational/sensory context may eventually propose semantic frames, but Vayu independently validates cognitive meaning through versioned contracts. No KUPPA runtime dependency is introduced.

## Rollback point

`dbfcb1dcfb089e4b1c9ce61f62d0c6fc828721ae`

## Lesson

An intelligent system should not treat structured output as truth merely because an LLM emitted valid JSON. Meaning needs its own trust boundary: admissible schema, source anchoring, uncertainty, modality consistency and abstention before durable belief.

## Next proposed target

Add a provider-isolated semantic extractor that converts deterministic structured device/browser/file events into `SemanticFrame` proposals and routes them through this boundary. Only after that path is measurable should Vayu add LLM semantic extraction, paired with a critic/verifier that checks claims against source evidence and existing World Model state before grounding.
