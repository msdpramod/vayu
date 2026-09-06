# 2026-09-07 03:57 — Corpus Factory admission boundary

## Hypothesis

The highest-leverage next step after Source Registry governance is a deterministic document-admission gate that can reject unsafe or invalid training candidates before Vayu acquires large corpora or starts Model Foundry work. Rights alone are not enough: individual records can still contain duplicates, secrets/PII, benchmark contamination, malformed content, or unstable split behavior.

## Architectural context

Vayu is the BRAIN; KUPPA AI is the HEART. This increment belongs entirely to Vayu's Dataset + World Learning Organ. It extends the Training/Corpus pipeline only and does not change KUPPA runtime behavior, grant execution authority, add external acquisition, or modify model weights.

Known-good baseline before feature work: `0b6a8dfd00b675bb437ccd36e0d3250b64bc54e4` (`v2026.09.06`). The latest `main` GitHub Actions CI run #259 completed successfully for that commit before this evolution began.

The local execution environment could not resolve `github.com`, so the complete repository could not be cloned independently. The new Corpus Factory logic was nevertheless exercised in an isolated local Python fixture harness before publication, where its eight focused tests passed. Repository-wide validation is delegated to the existing GitHub Actions pytest gate before merge.

## Detailed changes

- Added `app/corpus_factory.py` as a deterministic, no-network training-candidate admission boundary.
- Required `SourceRegistry.authorize(source_id, TRAINING)` before content can be considered for admission.
- Added bounded candidate batches (1,000 maximum), bounded document size, bounded stable build identifiers, and bounded external record identifiers.
- Added Unicode NFC/newline normalization with repeated blank-line compaction before hashing and exact deduplication.
- Added SHA-256 content hashes as exact provenance and deduplication identifiers.
- Added exact benchmark-contamination rejection through a bounded explicit SHA-256 deny-list.
- Added high-precision basic credential-like secret detection and direct-contact PII detection; matching records are rejected rather than scrubbed into silent training candidates.
- Added deterministic train/validation/test assignment derived from content hashes.
- Added lexical token estimates for build observability without claiming tokenizer-specific counts.
- Added immutable accepted/rejected record contracts and manifest schema v1.
- Manifest JSON includes dataset version, counts, token estimate, source/split/rejection breakdowns, license coverage and admitted hashes, while deliberately excluding raw corpus text.
- Dataset-version fingerprints incorporate build ID plus admitted source/external ID/content hash/license/attribution/split metadata so provenance changes are version-visible.
- Added ADR 0006 documenting corpus admission as a fail-closed training boundary.

## Files/components affected

- `app/corpus_factory.py`
- `tests/test_corpus_factory.py`
- `docs/adr/0006-corpus-admission-boundary.md`
- `VERSION`
- `CHANGELOG.md`
- `docs/evolution/README.md`
- `docs/evolution/2026/09/2026-09-07-0357-corpus-admission.md`

## Before / after behavior

Before: Vayu could decide whether a registered source family was authorized for training, but there was no document-level gate. An authorized source record had no reusable boundary for content normalization, exact deduplication, privacy/secret filtering, benchmark contamination checks, deterministic splits, token estimates, or corpus-manifest evidence.

After: candidate documents can only become in-memory training candidates after source-level training authorization and deterministic content-level admission checks. Accepted candidates carry source license/attribution provenance and stable content hashes; rejected candidates carry explicit machine-readable rejection reasons. A deterministic manifest summarizes the build without copying raw content into the manifest.

## Dataset / model / source provenance

Released production dataset version: none. No large source corpus was downloaded, materialized, or committed in this evolution.

Corpus manifest schema: v1.

Model version: none. No tokenizer, training job, candidate model, production weights, or Model Arena promotion changed.

Source Registry: unchanged at schema v1 with five registered families. Only records already authorized for `TRAINING` may pass this new admission boundary. This evolution does not broaden source rights.

The test fixtures use synthetic/local text only. The secret and PII examples are deliberately synthetic pattern fixtures, not real credentials or personal records.

## Tests / checks

Focused local fixture validation passed 8 tests covering:

1. deterministic admission of explicitly licensed source content;
2. fail-closed rejection of a review-only/unlicensed source;
3. normalization-aware exact duplicate rejection;
4. synthetic credential-like secret rejection;
5. synthetic direct-contact PII rejection;
6. exact held-out benchmark contamination rejection;
7. deterministic manifest JSON that does not embed raw corpus text;
8. malformed contamination-registry hash rejection.

Additional assertions verify deterministic repeated builds, 100% explicit-license coverage for accepted fixture records, token estimates, and dataset-version changes when admitted content changes.

The branch must pass the repository-wide GitHub Actions `python -m pytest -q` gate before merge. This record does not claim a repository-wide CI pass until GitHub reports it.

## Metrics

Focused fixture harness:

- New focused tests: 8
- Focused tests passed before publication: 8/8
- Maximum candidates per build: 1,000
- Maximum normalized document size: 200,000 characters
- Contamination registry bound: 100,000 SHA-256 hashes
- Manifest raw-text fields: 0
- Source license coverage for accepted positive-path fixtures: 100%
- Large external documents downloaded: 0
- Production training tokens generated: 0
- Production model weights changed: 0
- Cognitive capability score changes: 0

No corpus-size or duplicate-rate claims are made for real datasets because none were acquired.

## License / provenance decisions

- Training authorization remains inherited exclusively from Source Registry; this layer cannot upgrade `REVIEW_REQUIRED` rights to `VERIFIED`.
- Accepted documents inherit the registry's explicit `license_id` and `attribution_required` fields.
- Dataset-version fingerprints include provenance-bearing source and license metadata so a materially different admission result produces a different version identifier.
- Public accessibility remains insufficient for training admission.

## Security / privacy / permissions

This increment tightens the training path and adds no consequential external action.

- No network client or crawler was added.
- No raw OAuth/access/refresh tokens, passwords, cookies, or repository secrets were introduced.
- No arbitrary shell execution or self-modification capability was added.
- No model can alter Source Registry rights or bypass the admission checks.
- Basic secret/PII matches are rejected; raw rejected content is not emitted into the manifest.
- Benchmark contamination is deny-list based and fail-closed for malformed registry entries.
- Owner/personal memory is not connected to the corpus path.

## Rejected sources / content

No Source Registry entries were changed today. Review-required, incompatible, disabled, or otherwise non-training-authorized sources continue to fail closed.

At the document layer, the new boundary rejects malformed identifiers/text, empty normalized content, oversized documents, exact duplicates, exact benchmark-contamination matches, basic credential-like secrets, and direct email/phone-style contact identifiers.

## Failures / fallbacks tested

Failure paths explicitly validated include training-rights denial, normalization-driven duplicate detection, credential-like secret detection, direct-contact PII detection, exact benchmark contamination, and malformed contamination hashes.

If a candidate is rejected, the factory records a bounded reason and continues processing the remaining candidate batch; it does not silently coerce rejected material into accepted training data.

If the GitHub repository test gate fails, this branch must not be merged. The prior main commit remains the rollback point.

## Rollback

Rollback reference: `0b6a8dfd00b675bb437ccd36e0d3250b64bc54e4` (`v2026.09.06`). Reverting this evolution removes document-level corpus admission and returns to Source Registry-only governance.

## Known limitations / technical debt

- Secret/PII checks are basic high-precision heuristics, not comprehensive privacy detection.
- Near-duplicate/minhash/semantic deduplication is not implemented.
- Benchmark contamination is exact-hash only; substring/semantic overlap detection remains pending.
- Token counts are lexical estimates and are not tied to a Vayu-native tokenizer yet.
- Language/domain classification and domain-balance targets are not implemented.
- Durable corpus storage, signed/checksummed acquisition manifests, source retrieval timestamps and artifact stores are not implemented.
- No source adapter feeds candidates into Corpus Factory yet.
- No Right-to-Forget exclusion registry is connected yet.
- No Model Foundry or Model Arena training/promotion path consumes manifests yet.
- No World Pulse or Knowledge Genome change is included today; stable-training and fresh-world pipelines remain deliberately separated.

## Dependencies

Python standard library only. No new runtime dependency is introduced.

## Follow-up work

The next highest-leverage target is a versioned acquisition/provenance envelope plus durable contamination and deletion-exclusion registries. It should let an authorized source adapter emit bounded candidate records with acquisition timestamp, upstream artifact checksum/version, parser version and storage reference, then let Corpus Factory verify checksum/provenance before admission. A small fixture-backed adapter should be built before any large download.

After that, add near-deduplication, language/domain classification, domain-balance metrics, tokenizer-specific counts, and a Right-to-Forget exclusion gate before connecting any controlled Model Foundry training candidate.

World Pulse should evolve independently toward timestamped Knowledge Genome evidence rather than feeding rapidly changing facts into model weights.

## Next evolution target

Acquisition provenance envelope + checksum verification + durable contamination/deletion-exclusion registries, exercised only with small safe fixtures and explicit source authorization.
