# Vayu cognitive evolution — 2026-08-27

## Domain

Reasoning — critic / verifier loop.

## Observed state

Main was at `f59c6ec6011c5b9f9adb7991854a3a87d4bfd901` (`v2026.08.26`). GitHub Actions CI run #151 for that commit completed successfully. The semantic-understanding layer could reject malformed or ungrounded semantic frames, but once a frame passed that boundary there was no independent cognitive process challenging it against current world knowledge before grounding.

## Hypothesis

A second, independently implemented verification pass should reduce silent belief replacement and confidence escalation. The critic should not reinterpret language or execute actions; it should challenge an already-admitted semantic claim using source confidence and bounded current World Model context.

This is higher leverage than immediately adding another sensor because future deterministic and LLM extractors both need a trustworthy post-extraction checkpoint.

## Implementation

Added `app/critic.py` with:

- `CriticDisposition`: `verified`, `abstain`, `conflict`;
- immutable `CriticVerdict` carrying candidate and conflicting fact IDs;
- exact observation/semantic/candidate identity checks;
- a hard rule preventing candidate confidence from exceeding source-observation confidence;
- bounded World Model context (`MAX_CONTEXT_FACTS = 32`);
- current-fact-only contradiction review;
- abstention when substantially stronger contradictory evidence exists;
- explicit conflict surfacing for credible competing beliefs instead of silently overwriting them;
- no confidence boost for matching prior beliefs.

Added regression coverage for verified claims, upstream abstention, confidence escalation, stronger contradictions, close conflicts, historical evidence, matching evidence, cross-observation isolation, and context bounds.

## Evidence / score

Reasoning moves conservatively from `0.48` to `0.50`. This change is intentionally small: Vayu now has one independent semantic critic, but it still lacks general plan criticism, causal simulation, multi-hypothesis reasoning, and verifier diversity.

No other cognitive score changed.

## Safety / regression impact

The critic is cognition-only. It has no persistence, model, network, planner, executor, permission, approval, action-store, or external-side-effect authority. A `conflict` verdict is not an approval signal. Existing execution controls, payload policy, confirmation TTL, idempotency, and least-privilege boundaries are unchanged.

## KUPPA pattern reused

The useful KUPPA principle remains separation of cognition from authority: Vayu may reason more deeply about whether a belief is credible, while action authority remains independently gated. No runtime dependency on KUPPA AI was introduced.

## Rollback point

`f59c6ec6011c5b9f9adb7991854a3a87d4bfd901`

## Lesson

Schema-valid structured output is still only a proposal. Reliable cognition needs an adversarial second process that asks whether the claim is consistent with the original evidence and with what the system already believes, while being willing to return uncertainty rather than forcing a conclusion.

## Next target

Build a deterministic semantic extractor for device/browser/file observations and route its output through `SemanticUnderstandingBoundary -> SemanticCritic -> CognitiveGroundingGateway`. Once deterministic extraction is measurable, generalize the same proposal/critic/verifier pattern to planner reasoning and simulation.
