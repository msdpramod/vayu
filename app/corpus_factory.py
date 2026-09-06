from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from app.source_registry import SourcePurpose, SourceRecord, SourceRegistry

MAX_CANDIDATES = 1000
MAX_DOCUMENT_CHARS = 200_000
MAX_EXTERNAL_ID = 240
MAX_BUILD_ID = 120

_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d .()-]{7,}\d)(?!\d)")
_SECRET_PATTERNS = (
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


class RejectionReason(str, Enum):
    RIGHTS_DENIED = "rights_denied"
    INVALID_DOCUMENT = "invalid_document"
    EMPTY = "empty"
    TOO_LARGE = "too_large"
    SECRET_DETECTED = "secret_detected"
    PII_DETECTED = "pii_detected"
    EXACT_DUPLICATE = "exact_duplicate"
    BENCHMARK_CONTAMINATION = "benchmark_contamination"


class CorpusSplit(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


@dataclass(frozen=True)
class CorpusCandidate:
    source_id: str
    external_id: str
    text: str


@dataclass(frozen=True)
class AdmittedDocument:
    source_id: str
    external_id: str
    normalized_text: str
    content_sha256: str
    license_id: str
    attribution_required: bool
    split: CorpusSplit
    token_estimate: int


@dataclass(frozen=True)
class RejectedDocument:
    source_id: str
    external_id: str
    reason: RejectionReason
    detail: str
    content_sha256: str | None = None


@dataclass(frozen=True)
class CorpusManifest:
    schema_version: int
    build_id: str
    dataset_version: str
    accepted_count: int
    rejected_count: int
    token_estimate: int
    exact_duplicate_count: int
    pii_rejection_count: int
    secret_rejection_count: int
    contamination_rejection_count: int
    license_coverage: float
    source_counts: tuple[tuple[str, int], ...]
    split_counts: tuple[tuple[str, int], ...]
    rejection_counts: tuple[tuple[str, int], ...]
    admitted_hashes: tuple[str, ...]

    def to_json(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "build_id": self.build_id,
            "dataset_version": self.dataset_version,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "token_estimate": self.token_estimate,
            "exact_duplicate_count": self.exact_duplicate_count,
            "pii_rejection_count": self.pii_rejection_count,
            "secret_rejection_count": self.secret_rejection_count,
            "contamination_rejection_count": self.contamination_rejection_count,
            "license_coverage": self.license_coverage,
            "source_counts": dict(self.source_counts),
            "split_counts": dict(self.split_counts),
            "rejection_counts": dict(self.rejection_counts),
            "admitted_hashes": list(self.admitted_hashes),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class CorpusBuild:
    accepted: tuple[AdmittedDocument, ...]
    rejected: tuple[RejectedDocument, ...]
    manifest: CorpusManifest


class CorpusFactory:
    """Deterministic, no-network training-candidate admission boundary."""

    def __init__(self, source_registry: SourceRegistry, contamination_hashes: Iterable[str] = ()):
        self._sources = source_registry
        hashes = tuple(contamination_hashes)
        if len(hashes) > 100_000:
            raise ValueError("contamination registry is too large")
        for value in hashes:
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("contamination hashes must be lowercase SHA-256")
        self._contamination_hashes = frozenset(hashes)

    def build(self, candidates: Iterable[CorpusCandidate], *, build_id: str) -> CorpusBuild:
        items = tuple(candidates)
        if not build_id or len(build_id) > MAX_BUILD_ID or not re.fullmatch(r"[A-Za-z0-9._-]+", build_id):
            raise ValueError("build_id is required and must be a bounded stable identifier")
        if len(items) > MAX_CANDIDATES:
            raise ValueError(f"corpus build exceeds {MAX_CANDIDATES} candidates")

        accepted: list[AdmittedDocument] = []
        rejected: list[RejectedDocument] = []
        seen_hashes: set[str] = set()

        for candidate in items:
            rejection, source = self._preflight(candidate)
            if rejection is not None:
                rejected.append(rejection)
                continue

            normalized = self._normalize(candidate.text)
            if not normalized:
                rejected.append(self._reject(candidate, RejectionReason.EMPTY, "normalized content is empty"))
                continue
            if len(normalized) > MAX_DOCUMENT_CHARS:
                rejected.append(self._reject(candidate, RejectionReason.TOO_LARGE, "document exceeds character bound"))
                continue

            digest = self._hash(normalized)
            if digest in seen_hashes:
                rejected.append(
                    self._reject(
                        candidate,
                        RejectionReason.EXACT_DUPLICATE,
                        "normalized content duplicates an earlier candidate",
                        digest,
                    )
                )
                continue
            if digest in self._contamination_hashes:
                rejected.append(
                    self._reject(
                        candidate,
                        RejectionReason.BENCHMARK_CONTAMINATION,
                        "content hash matches contamination registry",
                        digest,
                    )
                )
                continue
            if self._contains_secret(normalized):
                rejected.append(
                    self._reject(candidate, RejectionReason.SECRET_DETECTED, "credential-like material detected", digest)
                )
                continue
            if self._contains_pii(normalized):
                rejected.append(
                    self._reject(candidate, RejectionReason.PII_DETECTED, "direct contact identifier detected", digest)
                )
                continue

            seen_hashes.add(digest)
            assert source is not None and source.license_id is not None
            accepted.append(
                AdmittedDocument(
                    source_id=candidate.source_id,
                    external_id=candidate.external_id,
                    normalized_text=normalized,
                    content_sha256=digest,
                    license_id=source.license_id,
                    attribution_required=source.attribution_required,
                    split=self._split_for(digest),
                    token_estimate=len(_TOKEN_RE.findall(normalized)),
                )
            )

        manifest = self._manifest(build_id, accepted, rejected)
        return CorpusBuild(tuple(accepted), tuple(rejected), manifest)

    def _preflight(self, candidate: CorpusCandidate) -> tuple[RejectedDocument | None, SourceRecord | None]:
        if (
            not candidate.source_id
            or len(candidate.source_id) > 120
            or not candidate.external_id
            or len(candidate.external_id) > MAX_EXTERNAL_ID
        ):
            return (
                self._reject(
                    candidate,
                    RejectionReason.INVALID_DOCUMENT,
                    "source_id and external_id are required and bounded",
                ),
                None,
            )
        if not isinstance(candidate.text, str):
            return self._reject(candidate, RejectionReason.INVALID_DOCUMENT, "text must be a string"), None
        try:
            source = self._sources.authorize(candidate.source_id, SourcePurpose.TRAINING)
        except (LookupError, KeyError, PermissionError):
            return (
                self._reject(candidate, RejectionReason.RIGHTS_DENIED, "source is not authorized for training"),
                None,
            )
        return None, source

    @staticmethod
    def _normalize(text: str) -> str:
        value = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in value.split("\n")]
        compact: list[str] = []
        blank = False
        for line in lines:
            if not line:
                if blank:
                    continue
                blank = True
            else:
                blank = False
            compact.append(line)
        return "\n".join(compact).strip()

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _contains_secret(text: str) -> bool:
        return any(pattern.search(text) for pattern in _SECRET_PATTERNS)

    @staticmethod
    def _contains_pii(text: str) -> bool:
        return bool(_EMAIL_RE.search(text) or _PHONE_RE.search(text))

    @staticmethod
    def _split_for(content_sha256: str) -> CorpusSplit:
        bucket = int(content_sha256[:8], 16) % 100
        if bucket < 80:
            return CorpusSplit.TRAIN
        if bucket < 90:
            return CorpusSplit.VALIDATION
        return CorpusSplit.TEST

    @staticmethod
    def _reject(
        candidate: CorpusCandidate,
        reason: RejectionReason,
        detail: str,
        digest: str | None = None,
    ) -> RejectedDocument:
        source_id = candidate.source_id if isinstance(candidate.source_id, str) else "<invalid>"
        external_id = candidate.external_id if isinstance(candidate.external_id, str) else "<invalid>"
        return RejectedDocument(source_id, external_id, reason, detail, digest)

    @staticmethod
    def _manifest(
        build_id: str,
        accepted: list[AdmittedDocument],
        rejected: list[RejectedDocument],
    ) -> CorpusManifest:
        source_counts = Counter(item.source_id for item in accepted)
        split_counts = Counter(item.split.value for item in accepted)
        rejection_counts = Counter(item.reason.value for item in rejected)
        admitted_hashes = tuple(sorted(item.content_sha256 for item in accepted))
        provenance_rows = sorted(
            f"{item.source_id}|{item.external_id}|{item.content_sha256}|{item.license_id}|"
            f"{int(item.attribution_required)}|{item.split.value}"
            for item in accepted
        )
        fingerprint_material = "\n".join((build_id, *provenance_rows)).encode("utf-8")
        dataset_version = f"corpus-v1-{hashlib.sha256(fingerprint_material).hexdigest()[:16]}"
        accepted_count = len(accepted)
        licensed = sum(1 for item in accepted if item.license_id)
        return CorpusManifest(
            schema_version=1,
            build_id=build_id,
            dataset_version=dataset_version,
            accepted_count=accepted_count,
            rejected_count=len(rejected),
            token_estimate=sum(item.token_estimate for item in accepted),
            exact_duplicate_count=rejection_counts[RejectionReason.EXACT_DUPLICATE.value],
            pii_rejection_count=rejection_counts[RejectionReason.PII_DETECTED.value],
            secret_rejection_count=rejection_counts[RejectionReason.SECRET_DETECTED.value],
            contamination_rejection_count=rejection_counts[RejectionReason.BENCHMARK_CONTAMINATION.value],
            license_coverage=(licensed / accepted_count if accepted_count else 1.0),
            source_counts=tuple(sorted(source_counts.items())),
            split_counts=tuple(sorted(split_counts.items())),
            rejection_counts=tuple(sorted(rejection_counts.items())),
            admitted_hashes=admitted_hashes,
        )
