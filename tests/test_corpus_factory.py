import hashlib

import pytest

from app.corpus_factory import CorpusCandidate, CorpusFactory, RejectionReason
from app.source_registry import RightsStatus, SourcePurpose, SourceRecord, SourceRegistry


def _source(source_id="wikidata-dumps", *, training=True):
    uses = (SourcePurpose.TRAINING,) if training else (SourcePurpose.RETRIEVAL,)
    rights = RightsStatus.VERIFIED if training else RightsStatus.REVIEW_REQUIRED
    return SourceRecord(
        source_id=source_id,
        purposes=(SourcePurpose.TRAINING, SourcePurpose.RETRIEVAL),
        official_reference="https://example.org/data",
        rights_status=rights,
        license_id="CC0-1.0" if training else None,
        allowed_uses=uses,
        attribution_required=False,
        acquisition_method="fixture",
        freshness_expectation="static",
        trust_tier=1,
        privacy_notes="fixture",
        rate_limit_notes="none",
        parser_version="v1",
        enabled=True,
    )


def test_build_admits_licensed_content_and_is_deterministic():
    factory = CorpusFactory(SourceRegistry([_source()]))
    candidates = [
        CorpusCandidate("wikidata-dumps", "q1", "Ada Lovelace wrote notes on the Analytical Engine."),
        CorpusCandidate(
            "wikidata-dumps",
            "q2",
            "Dijkstra's algorithm computes shortest paths for non-negative edges.",
        ),
    ]
    first = factory.build(candidates, build_id="2026-09-07-fixture")
    second = factory.build(candidates, build_id="2026-09-07-fixture")

    assert first == second
    assert first.manifest.accepted_count == 2
    assert first.manifest.rejected_count == 0
    assert first.manifest.license_coverage == 1.0
    assert first.manifest.token_estimate > 0
    assert all(item.license_id == "CC0-1.0" for item in first.accepted)


def test_unlicensed_source_fails_closed_before_content_admission():
    factory = CorpusFactory(SourceRegistry([_source("review-only", training=False)]))

    build = factory.build(
        [CorpusCandidate("review-only", "doc", "Safe public text.")],
        build_id="rights",
    )

    assert build.accepted == ()
    assert build.rejected[0].reason is RejectionReason.RIGHTS_DENIED


def test_exact_duplicate_is_rejected_after_normalization():
    factory = CorpusFactory(SourceRegistry([_source()]))

    build = factory.build(
        [
            CorpusCandidate("wikidata-dumps", "a", "same text\n\n\nwith spacing"),
            CorpusCandidate("wikidata-dumps", "b", "same text\n\nwith spacing"),
        ],
        build_id="dedup",
    )

    assert build.manifest.accepted_count == 1
    assert build.manifest.exact_duplicate_count == 1
    assert build.rejected[0].reason is RejectionReason.EXACT_DUPLICATE


def test_secret_and_pii_are_rejected_and_not_in_admitted_hashes():
    factory = CorpusFactory(SourceRegistry([_source()]))

    build = factory.build(
        [
            CorpusCandidate(
                "wikidata-dumps",
                "secret",
                "synthetic credential AKIAABCDEFGHIJKLMNOP must never train",
            ),
            CorpusCandidate(
                "wikidata-dumps",
                "pii",
                "contact synthetic-researcher@example.org for details",
            ),
        ],
        build_id="privacy",
    )

    assert build.manifest.secret_rejection_count == 1
    assert build.manifest.pii_rejection_count == 1
    assert build.manifest.accepted_count == 0
    assert build.manifest.admitted_hashes == ()


def test_benchmark_contamination_hash_is_rejected():
    text = "held-out benchmark fixture answer"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    factory = CorpusFactory(SourceRegistry([_source()]), contamination_hashes=[digest])

    build = factory.build(
        [CorpusCandidate("wikidata-dumps", "bench", text)],
        build_id="contamination",
    )

    assert build.rejected[0].reason is RejectionReason.BENCHMARK_CONTAMINATION
    assert build.manifest.contamination_rejection_count == 1


def test_dataset_version_changes_when_admitted_content_changes():
    factory = CorpusFactory(SourceRegistry([_source()]))

    a = factory.build(
        [CorpusCandidate("wikidata-dumps", "a", "alpha stable fact")],
        build_id="same",
    )
    b = factory.build(
        [CorpusCandidate("wikidata-dumps", "b", "beta stable fact")],
        build_id="same",
    )

    assert a.manifest.dataset_version != b.manifest.dataset_version


def test_manifest_json_is_deterministic_and_does_not_embed_raw_text():
    factory = CorpusFactory(SourceRegistry([_source()]))
    build = factory.build(
        [CorpusCandidate("wikidata-dumps", "doc", "stable corpus sentence")],
        build_id="manifest",
    )

    payload = build.manifest.to_json()

    assert payload == build.manifest.to_json()
    assert "stable corpus sentence" not in payload
    assert build.accepted[0].content_sha256 in payload


def test_malformed_contamination_hash_registry_fails_closed():
    with pytest.raises(ValueError, match="SHA-256"):
        CorpusFactory(SourceRegistry([_source()]), contamination_hashes=["not-a-hash"])
