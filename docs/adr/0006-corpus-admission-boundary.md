# ADR 0006 — Corpus admission is a fail-closed training boundary

## Status

Accepted — 2026-09-07

## Context

Vayu's Source Registry now distinguishes source availability from explicit training authorization, but source-level rights are not sufficient to make individual documents safe training candidates. Raw content can still contain duplicate material, direct personal identifiers, credential-like secrets, benchmark answers, malformed records, or provenance that should not enter a model-development pipeline.

The Dataset + World Learning Organ needs a deterministic gate between authorized source acquisition and any future Vayu Corpus Factory storage or Model Foundry training job. This gate must not depend on an LLM and must not perform acquisition or training itself.

## Decision

Introduce a deterministic `CorpusFactory` admission boundary with the following ordering and invariants:

1. A candidate must identify a bounded source and external record identifier.
2. The source must pass `SourceRegistry.authorize(..., TRAINING)` before content admission.
3. Content is normalized deterministically and bounded in size.
4. SHA-256 is used as the stable exact-content provenance and deduplication key.
5. Exact duplicate content is rejected within the build.
6. Exact benchmark-contamination hashes are rejected before admission.
7. Basic credential-like secrets and direct contact identifiers are rejected rather than silently entering the candidate corpus.
8. Accepted content inherits the source license and attribution requirement.
9. Train/validation/test assignment is deterministic from the content hash, preventing random split drift between equivalent builds.
10. Manifest schema v1 records counts, token estimates, rejection metrics, license coverage, split/source balance and admitted hashes, but deliberately omits raw corpus text.
11. Dataset-version fingerprints include admitted content hashes plus source/provenance/license/split metadata and the explicit build identifier.

The boundary is no-network and side-effect-free. It cannot download sources, modify Source Registry rights, train or promote models, mutate production weights, or authorize external actions.

## Consequences

Positive:

- Training-rights checks become mandatory at document admission rather than relying on operator convention.
- Exact duplicate, secret/PII and held-out benchmark contamination failure paths become testable before large corpus acquisition exists.
- Dataset manifests can be compared reproducibly without exposing raw training text.
- Deterministic splitting reduces accidental benchmark leakage caused by rerunning random split logic.
- Future acquisition adapters and Model Foundry jobs get a narrow contract instead of direct raw-source coupling.

Trade-offs and limitations:

- Secret/PII detection is intentionally basic and high-precision; it is not a complete privacy classifier.
- Only exact deduplication and exact-hash contamination are implemented; near-duplicate and semantic contamination checks remain future work.
- Token counts are lexical estimates, not tokenizer-specific training token counts.
- Domain/language classification and domain balancing are not yet part of admission.
- Accepted documents remain in memory; durable corpus storage and manifest persistence require a separate controlled storage design.

## Security and privacy

This decision narrows training admission. A document from a publicly reachable source still cannot pass unless its source is explicitly training-authorized. Content that matches the current secret, direct-contact PII, duplicate, or contamination checks is rejected and its raw text is not included in the manifest.

No secrets, OAuth material, unrestricted shell capability, network acquisition, model mutation, approval bypass, or self-modification authority is introduced.

## Rollback

Revert the v2026.09.07 corpus-admission evolution to return to Source Registry-only governance. The known-good pre-change baseline is `0b6a8dfd00b675bb437ccd36e0d3250b64bc54e4` (`v2026.09.06`).
