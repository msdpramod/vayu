from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable


MAX_SOURCES = 256
MAX_ALLOWED_USES = 8
MAX_TEXT = 500


class SourcePurpose(str, Enum):
    TRAINING = "TRAINING"
    RETRIEVAL = "RETRIEVAL"
    EVALUATION = "EVALUATION"
    METADATA = "METADATA"


class RightsStatus(str, Enum):
    VERIFIED = "VERIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INCOMPATIBLE = "INCOMPATIBLE"


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    purposes: tuple[SourcePurpose, ...]
    official_reference: str
    rights_status: RightsStatus
    license_id: str | None
    allowed_uses: tuple[SourcePurpose, ...]
    attribution_required: bool
    acquisition_method: str
    freshness_expectation: str
    trust_tier: int
    privacy_notes: str
    rate_limit_notes: str
    parser_version: str
    enabled: bool

    @property
    def training_allowed(self) -> bool:
        return (
            self.enabled
            and SourcePurpose.TRAINING in self.purposes
            and SourcePurpose.TRAINING in self.allowed_uses
            and self.rights_status is RightsStatus.VERIFIED
            and bool(self.license_id)
        )


class SourceRegistry:
    """Fail-closed registry separating source availability from training permission."""

    def __init__(self, records: Iterable[SourceRecord]):
        items = tuple(records)
        if not items or len(items) > MAX_SOURCES:
            raise ValueError(f"source registry must contain between 1 and {MAX_SOURCES} records")
        self._records: dict[str, SourceRecord] = {}
        for record in items:
            self._validate(record)
            if record.source_id in self._records:
                raise ValueError(f"duplicate source_id: {record.source_id}")
            self._records[record.source_id] = record

    @classmethod
    def from_json(cls, path: str | Path) -> "SourceRegistry":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("unsupported source registry schema")
        raw_sources = payload.get("sources")
        if not isinstance(raw_sources, list):
            raise ValueError("sources must be a list")
        return cls(cls._parse_record(item) for item in raw_sources)

    @staticmethod
    def _parse_record(item: object) -> SourceRecord:
        if not isinstance(item, dict):
            raise ValueError("source record must be an object")
        try:
            return SourceRecord(
                source_id=str(item["source_id"]),
                purposes=tuple(SourcePurpose(value) for value in item["purposes"]),
                official_reference=str(item["official_reference"]),
                rights_status=RightsStatus(str(item["rights_status"])),
                license_id=(str(item["license_id"]) if item.get("license_id") else None),
                allowed_uses=tuple(SourcePurpose(value) for value in item["allowed_uses"]),
                attribution_required=bool(item["attribution_required"]),
                acquisition_method=str(item["acquisition_method"]),
                freshness_expectation=str(item["freshness_expectation"]),
                trust_tier=int(item["trust_tier"]),
                privacy_notes=str(item["privacy_notes"]),
                rate_limit_notes=str(item["rate_limit_notes"]),
                parser_version=str(item["parser_version"]),
                enabled=bool(item["enabled"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid source registry record") from exc

    @staticmethod
    def _validate(record: SourceRecord) -> None:
        if not record.source_id or len(record.source_id) > 120:
            raise ValueError("source_id is required and bounded")
        if not record.official_reference.startswith("https://") or len(record.official_reference) > MAX_TEXT:
            raise ValueError("official_reference must be a bounded HTTPS URL")
        if not record.purposes or len(set(record.purposes)) != len(record.purposes):
            raise ValueError("purposes must be non-empty and unique")
        if len(record.allowed_uses) > MAX_ALLOWED_USES or len(set(record.allowed_uses)) != len(record.allowed_uses):
            raise ValueError("allowed_uses must be bounded and unique")
        if not set(record.allowed_uses).issubset(set(record.purposes)):
            raise ValueError("allowed_uses must be declared purposes")
        if not 1 <= record.trust_tier <= 5:
            raise ValueError("trust_tier must be between 1 and 5")
        for value in (
            record.acquisition_method,
            record.freshness_expectation,
            record.privacy_notes,
            record.rate_limit_notes,
            record.parser_version,
        ):
            if not value or len(value) > MAX_TEXT:
                raise ValueError("source metadata fields are required and bounded")
        if record.rights_status is RightsStatus.INCOMPATIBLE and SourcePurpose.TRAINING in record.allowed_uses:
            raise ValueError("incompatible sources cannot allow training")
        if SourcePurpose.TRAINING in record.allowed_uses and (
            record.rights_status is not RightsStatus.VERIFIED or not record.license_id
        ):
            raise ValueError("training requires verified rights and an explicit license")

    def get(self, source_id: str) -> SourceRecord:
        try:
            return self._records[source_id]
        except KeyError as exc:
            raise LookupError(f"source not registered: {source_id}") from exc

    def authorize(self, source_id: str, purpose: SourcePurpose) -> SourceRecord:
        record = self.get(source_id)
        if not record.enabled:
            raise PermissionError("source is disabled")
        if purpose not in record.allowed_uses:
            raise PermissionError(f"source is not authorized for {purpose.value.lower()}")
        if purpose is SourcePurpose.TRAINING and not record.training_allowed:
            raise PermissionError("source is not cleared for training")
        return record

    def enabled_for(self, purpose: SourcePurpose) -> tuple[SourceRecord, ...]:
        return tuple(
            record
            for record in self._records.values()
            if record.enabled and purpose in record.allowed_uses and (purpose is not SourcePurpose.TRAINING or record.training_allowed)
        )
