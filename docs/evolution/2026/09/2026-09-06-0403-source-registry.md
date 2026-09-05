# 2026-09-06 04:03 — Dataset + World Learning Source Registry

## Hypothesis

The highest-leverage first increment for Vayu's Dataset + World Learning Organ is not a downloader or crawler. It is a fail-closed source-rights registry that makes training permission an explicit machine-checkable decision before any acquisition pipeline exists. Without this boundary, future corpus builders could accidentally treat public accessibility as permission to train.

## Architectural context

Vayu is the BRAIN; KUPPA AI is the HEART. This increment belongs to Vayu's Dataset + World Learning Organ and establishes a shared governance boundary for both the Training/Corpus pipeline and future World Pulse retrieval. It does not add autonomous acquisition, model training, external side effects, or KUPPA runtime coupling.

The known-good baseline is `e57fe29c56de9e142b6043e12f85513d97e46171` (`v2026.09.05`). Its `main` GitHub Actions CI run #256 completed successfully on 2026-09-04 UTC before feature work began.

## Detailed changes

- Added `app/source_registry.py` with bounded immutable source records and a fail-closed registry.
- Added explicit purposes: `TRAINING`, `RETRIEVAL`, `EVALUATION`, and `METADATA`.
- Added rights states: `VERIFIED`, `REVIEW_REQUIRED`, and `INCOMPATIBLE`.
- Training authorization now requires: enabled source, declared training purpose, explicit training use, verified rights, and a concrete license identifier.
- Retrieval/metadata authorization is deliberately separate from training authorization.
- Registry validation rejects duplicate source IDs, non-HTTPS official references, malformed/broad metadata, inconsistent allowed uses, incompatible training declarations, and training declarations without verified rights/license.
- Added `data/source_registry.json` as a small auditable registry manifest rather than committing source datasets.
- Seeded candidate source families for Wikidata dumps, English Wikipedia dumps, GDELT, NVD/CVE, and public GitHub code.
- Kept GitHub public-code acquisition disabled by default; repository-level licenses and secret scanning are still required before future use.
- Marked Wikipedia, GDELT and NVD training rights as review-required rather than assuming public availability equals model-training permission.
- Added ADR 0005 defining source rights as an authorization boundary.

## Files/components affected

- `app/source_registry.py`
- `tests/test_source_registry.py`
- `data/source_registry.json`
- `docs/adr/0005-source-rights-authorization-boundary.md`
- `VERSION`
- `CHANGELOG.md`
- `docs/evolution/README.md`
- `docs/evolution/2026/09/2026-09-06-0403-source-registry.md`

## Before / after behavior

Before: Vayu had no Dataset + World Learning source-governance code. A future builder would have had no central machine-readable distinction between retrieval permission and training permission.

After: every future source adapter or corpus builder can be required to resolve a registered source and request authorization for a specific purpose. Training fails closed unless rights are explicitly verified and licensed. Retrieval can remain independently allowed where appropriate.

## Dataset / model / source provenance

Dataset version: none. No corpus was downloaded or generated.

Model version: none. No model weights were trained or modified.

Source-registry schema: v1.

Initial registry contains five source families. Only `wikidata-dumps` is explicitly training-authorized in this first manifest; the others are retrieval/metadata-only or disabled pending stronger source-specific policy. Registry metadata itself is committed; raw datasets are not.

## Tests/checks

New regression scenarios cover:

1. verified licensed source authorizes training;
2. review-required source remains usable for explicitly allowed retrieval but fails closed for training;
3. incompatible source cannot declare training use;
4. training use without verified rights/license is rejected at registry construction;
5. disabled source cannot be authorized;
6. duplicate source IDs fail closed;
7. non-HTTPS official references fail validation.

The branch must pass the repository GitHub Actions pytest gate before merge. Final test count/result will be verified from CI; this record does not claim success before CI reports it.

## Metrics

- Source families registered: 5
- Explicitly training-authorized families: 1
- Training-authorized license coverage: 100% of authorized entries carry an explicit license identifier
- Raw documents acquired: 0
- Training tokens generated: 0
- Model weights changed: 0
- Cognitive capability scores changed: 0

## Security / privacy / permissions

This is a permission-tightening change. It adds no network access, scraper, downloader, model runtime, shell capability, external-action authority, or secret storage.

The registry requires privacy notes and separates rights state from technical availability. Future corpus builders still need PII/secret minimization, contamination checks, deduplication, and per-source attribution handling before any training candidate is accepted.

## Rejected / restricted sources

- Generic public GitHub code is disabled by default because each repository requires license/terms handling and secret scanning.
- English Wikipedia dumps are not training-authorized in this first pass; attribution/share-alike implications require an explicit policy rather than inference.
- GDELT and NVD are retrieval/metadata-only in this first pass; no training permission is inferred.
- Common Crawl is intentionally not yet registered because page-level rights filtering and terms policy need a more expressive adapter/manifest design.

## Failure/fallback testing

The registry fails closed for unclear training rights, incompatible rights, disabled sources, duplicate IDs, malformed records, and insecure official references. A rights-review failure does not require disabling lawful retrieval if retrieval was separately approved.

## Rollback

Rollback reference: `e57fe29c56de9e142b6043e12f85513d97e46171` (`v2026.09.05`). Reverting this evolution removes Source Registry v1 and returns to the prior Social Media Organ baseline.

## Known limitations / technical debt

- No source adapter consumes the registry yet.
- `last_successful_retrieval`, checksum/version and source-health observations are intentionally absent until acquisition exists; inventing them now would be false provenance.
- No corpus manifest, content hashing, exact/near deduplication, PII/secret filter, contamination registry, tokenizer or token estimator exists yet.
- Rights review is represented but not automated legal analysis.
- Source-specific attribution artifacts are not yet generated.
- No World Pulse evidence package or Knowledge Genome schema exists yet.

## Dependencies

Python standard library only. No new runtime dependency is introduced.

## Follow-up / next evolution target

Build the first deterministic `CorpusCandidate` admission boundary and manifest builder: require Source Registry training authorization, content hash/provenance, license inheritance, exact deduplication, basic secret/PII rejection, contamination deny-list checks, deterministic train/validation/test assignment, accepted/rejected counters, and a versioned small-fixture manifest. Do not download large corpora yet.
