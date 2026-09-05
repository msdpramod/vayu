# ADR 0005: Source rights are an explicit authorization boundary

- Status: Accepted
- Date: 2026-09-06

## Context

Vayu is beginning a Dataset + World Learning Organ with two different evidence paths: stable training corpora and fresh inference-time World Pulse retrieval. Public accessibility is not equivalent to permission to train. A source that is useful for transient retrieval may still have unclear, incompatible, attribution-heavy, repository-specific, or otherwise unverified training rights.

## Decision

Every external source family must be registered before acquisition with an explicit stable source ID, intended purposes, official reference, rights-review state, explicit allowed uses, attribution requirement, acquisition method, freshness expectation, trust tier, privacy notes, rate-limit notes, parser version, and enabled state.

Training authorization is fail-closed. `TRAINING` is permitted only when all of the following are true: the source is enabled; training is an intended purpose; training is explicitly listed in allowed uses; rights status is `VERIFIED`; and a concrete license identifier is recorded. `REVIEW_REQUIRED` and `INCOMPATIBLE` sources can never silently flow into training.

Retrieval and metadata use remain separately authorized. This lets Vayu use lawful transient evidence without converting the same material into model weights. Source adapters must consult this registry rather than hardcode rights assumptions.

The repository stores only registry metadata, builders, manifests, schemas and small safe fixtures. Large raw datasets remain outside ordinary Git.

## Consequences

- Training permission is machine-checkable and independent from source availability.
- A source can be allowed for retrieval but denied for training.
- Future Corpus Factory builders have a single rights gate before ingestion.
- Future World Pulse adapters can reuse source metadata for freshness, trust, privacy and rate-limit policy.
- Registry entries still require ongoing legal/terms review; code validation does not replace legal analysis.
- Changes to source rights, endpoints, parser versions or enabled state become auditable Git history.
