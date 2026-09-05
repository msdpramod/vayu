import json

import pytest

from app.source_registry import RightsStatus, SourcePurpose, SourceRecord, SourceRegistry


def _record(**overrides):
    values = dict(
        source_id="wikidata-dumps",
        purposes=(SourcePurpose.TRAINING, SourcePurpose.RETRIEVAL, SourcePurpose.METADATA),
        official_reference="https://dumps.wikimedia.org/wikidatawiki/entities/",
        rights_status=RightsStatus.VERIFIED,
        license_id="CC0-1.0",
        allowed_uses=(SourcePurpose.TRAINING, SourcePurpose.RETRIEVAL, SourcePurpose.METADATA),
        attribution_required=False,
        acquisition_method="official_dump",
        freshness_expectation="weekly snapshot or newer",
        trust_tier=1,
        privacy_notes="Public collaborative knowledge; downstream privacy filtering still required.",
        rate_limit_notes="Prefer published dumps over high-volume API acquisition.",
        parser_version="v1",
        enabled=True,
    )
    values.update(overrides)
    return SourceRecord(**values)


def test_verified_explicit_license_can_authorize_training():
    registry = SourceRegistry([_record()])

    record = registry.authorize("wikidata-dumps", SourcePurpose.TRAINING)

    assert record.training_allowed is True


def test_review_required_source_fails_closed_for_training():
    record = _record(
        source_id="public-web-candidate",
        rights_status=RightsStatus.REVIEW_REQUIRED,
        license_id=None,
        allowed_uses=(SourcePurpose.RETRIEVAL,),
    )
    registry = SourceRegistry([record])

    with pytest.raises(PermissionError, match="training"):
        registry.authorize("public-web-candidate", SourcePurpose.TRAINING)
    assert registry.authorize("public-web-candidate", SourcePurpose.RETRIEVAL) == record


def test_incompatible_source_cannot_declare_training_use():
    with pytest.raises(ValueError, match="incompatible"):
        SourceRegistry([
            _record(
                rights_status=RightsStatus.INCOMPATIBLE,
                allowed_uses=(SourcePurpose.TRAINING,),
            )
        ])


def test_training_use_requires_verified_rights_and_explicit_license():
    with pytest.raises(ValueError, match="verified rights"):
        SourceRegistry([
            _record(
                rights_status=RightsStatus.REVIEW_REQUIRED,
                license_id=None,
                allowed_uses=(SourcePurpose.TRAINING,),
            )
        ])


def test_disabled_source_is_never_authorized():
    registry = SourceRegistry([_record(enabled=False)])

    with pytest.raises(PermissionError, match="disabled"):
        registry.authorize("wikidata-dumps", SourcePurpose.RETRIEVAL)
    assert registry.enabled_for(SourcePurpose.TRAINING) == ()


def test_registry_loader_rejects_duplicate_ids(tmp_path):
    item = {
        "source_id": "duplicate",
        "purposes": ["RETRIEVAL"],
        "official_reference": "https://example.org/data",
        "rights_status": "REVIEW_REQUIRED",
        "license_id": None,
        "allowed_uses": ["RETRIEVAL"],
        "attribution_required": True,
        "acquisition_method": "official_api",
        "freshness_expectation": "daily",
        "trust_tier": 2,
        "privacy_notes": "Minimize personal data.",
        "rate_limit_notes": "Respect provider limits.",
        "parser_version": "v1",
        "enabled": True,
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"schema_version": 1, "sources": [item, item]}), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate source_id"):
        SourceRegistry.from_json(path)


def test_registry_loader_rejects_non_https_reference(tmp_path):
    item = {
        "source_id": "unsafe-endpoint",
        "purposes": ["RETRIEVAL"],
        "official_reference": "http://example.org/data",
        "rights_status": "REVIEW_REQUIRED",
        "license_id": None,
        "allowed_uses": ["RETRIEVAL"],
        "attribution_required": False,
        "acquisition_method": "official_api",
        "freshness_expectation": "daily",
        "trust_tier": 3,
        "privacy_notes": "None noted.",
        "rate_limit_notes": "Respect provider limits.",
        "parser_version": "v1",
        "enabled": True,
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"schema_version": 1, "sources": [item]}), encoding="utf-8")

    with pytest.raises(ValueError, match="HTTPS"):
        SourceRegistry.from_json(path)
