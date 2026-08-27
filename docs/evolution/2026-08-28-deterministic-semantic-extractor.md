# Vayu cognitive evolution — 2026-08-28

## Domain

Perception — deterministic semantic extraction.

## Observed state

Main was at `7be4b1de98729735e9ee6846162ec6e75d35cfdc` (`v2026.08.27`). GitHub Actions CI run #160 for that commit completed successfully. Vayu already had normalized perception, attention, schema-constrained semantic validation, an independent semantic critic, grounding, and a durable World Model. The missing link was a measurable extractor that could turn raw device/browser/file summaries into semantic proposals without relying on an LLM.

## Hypothesis

Before introducing probabilistic or LLM-backed extraction, Vayu should have a deterministic extractor with narrow, observable failure modes. Exact patterns provide a baseline for precision, abstention behavior, confidence preservation, and end-to-end integration through the existing semantic boundary and critic.

This is higher leverage than adding a live microphone/camera adapter because new sensory volume without a trustworthy extraction baseline would increase ambiguity rather than intelligence.

## Implementation

Added `app/semantic_extractor.py` with:

- exact allow-listed sentence patterns for device service status, browser page state, and file lifecycle observations;
- complete-string matching rather than fuzzy substring extraction;
- strict subject identifier syntax and bounded length;
- output confidence copied from source perception rather than boosted by the extractor;
- explicit abstention for unsupported modalities, ambiguous text, and non-matching summaries;
- bounded batches (`MAX_OBSERVATIONS = 32`) and duplicate observation rejection;
- no model, network, persistence, planner, executor, permission, approval, action-store, or side-effect authority.

Added regression coverage for all three supported schemas, ambiguous-text abstention, unsupported modalities, duplicate and batch bounds, confidence preservation, end-to-end passage through `SemanticUnderstandingBoundary -> SemanticCritic`, and low-confidence rejection at the semantic boundary.

## Evidence / score

Perception moves conservatively from `0.40` to `0.44` because Vayu now has an automatic deterministic extraction path for a narrow set of structured observations. This does not claim general natural-language understanding, live sensory integration, or LLM extraction.

No other cognitive score changed.

## Safety / regression impact

The extractor can only propose a `SemanticFrame`. It cannot persist facts or trigger actions. Its output must still pass the semantic boundary and independent critic before grounding. Existing execution approval, payload policy, idempotency, approval expiry, and least-privilege controls are unchanged.

## KUPPA pattern reused

The useful KUPPA principle remains separation of intelligence from authority: interpretation may become richer while action authority remains independently gated. No runtime dependency on KUPPA AI was introduced.

## Rollback point

`7be4b1de98729735e9ee6846162ec6e75d35cfdc`

## Lesson

A stronger cognitive system needs a known-precision baseline before probabilistic intelligence is layered on top. Deterministic extraction makes abstention and false-positive behavior measurable and gives future LLM extraction a contract it must beat rather than replace.

## Next target

Generalize the critic/verifier architecture to planner output: `Planner -> Plan Critic -> Simulation -> Approval Queue`. The next increment should first build a cognition-only plan critic that checks unsupported tool assumptions, missing preconditions, irreversible-risk indicators, and confidence/uncertainty before any proposed action can reach approval.
