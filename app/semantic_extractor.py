from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from app.perception import PerceptionModality, PerceptionObservation
from app.semantics import SemanticFrame


@dataclass(frozen=True)
class ExtractionResult:
    """Result of deterministic semantic extraction from one observation."""

    observation_id: str
    extracted: bool
    reason: str
    frame: SemanticFrame | None = None


class DeterministicSemanticExtractor:
    """Extracts only narrow, explicitly supported meanings from sensory evidence.

    This extractor intentionally does not perform fuzzy NLP. A summary must match one
    of the complete allow-listed sentence shapes below. Ambiguous or unsupported
    observations cause abstention. The output is still only a ``SemanticFrame`` and
    must pass ``SemanticUnderstandingBoundary`` and the independent critic before it
    may become durable World Model state.

    The extractor has no model, network, persistence, planner, executor, permission,
    approval, action-store, or external side-effect authority.
    """

    MAX_OBSERVATIONS = 32
    MAX_SUBJECT_ID = 128

    _SUBJECT = r"(?P<subject>[A-Za-z0-9][A-Za-z0-9._:/-]{0,127})"
    _PATTERNS: tuple[
        tuple[PerceptionModality, str, str, str, re.Pattern[str]], ...
    ] = (
        (
            PerceptionModality.DEVICE,
            "device.service_status.v1",
            "status",
            "service",
            re.compile(
                rf"^service\s+{_SUBJECT}\s+is\s+(?P<value>healthy|degraded|down|unknown)$",
                re.IGNORECASE,
            ),
        ),
        (
            PerceptionModality.BROWSER,
            "browser.page_state.v1",
            "state",
            "page",
            re.compile(
                rf"^page\s+{_SUBJECT}\s+is\s+(?P<value>loading|ready|error)$",
                re.IGNORECASE,
            ),
        ),
        (
            PerceptionModality.FILE,
            "file.lifecycle.v1",
            "state",
            "file",
            re.compile(
                rf"^file\s+{_SUBJECT}\s+was\s+(?P<value>created|modified|deleted)$",
                re.IGNORECASE,
            ),
        ),
    )

    @staticmethod
    def _canonical_summary(summary: str) -> str:
        return " ".join(summary.strip().split())

    def extract(self, observation: PerceptionObservation) -> ExtractionResult:
        summary = self._canonical_summary(observation.summary)

        modality_patterns = [item for item in self._PATTERNS if item[0] is observation.modality]
        if not modality_patterns:
            return ExtractionResult(
                observation.observation_id,
                False,
                "no deterministic semantic extractor is registered for this modality",
            )

        matches: list[tuple[str, str, re.Match[str]]] = []
        for _, schema, predicate, _, pattern in modality_patterns:
            match = pattern.fullmatch(summary)
            if match is not None:
                matches.append((schema, predicate, match))

        if len(matches) != 1:
            return ExtractionResult(
                observation.observation_id,
                False,
                "observation did not match exactly one deterministic semantic pattern",
            )

        schema, predicate, match = matches[0]
        subject_id = match.group("subject")
        value = match.group("value").casefold()
        if len(subject_id) > self.MAX_SUBJECT_ID:
            return ExtractionResult(observation.observation_id, False, "subject_id exceeds extractor limit")

        frame = SemanticFrame(
            observation_id=observation.observation_id,
            schema=schema,
            subject_id=subject_id,
            predicate=predicate,
            value=value,
            confidence=observation.confidence,
            evidence_span=summary,
        )
        return ExtractionResult(
            observation.observation_id,
            True,
            "deterministic semantic pattern matched",
            frame,
        )

    def extract_batch(self, observations: Iterable[PerceptionObservation]) -> list[ExtractionResult]:
        items = list(observations)
        if len(items) > self.MAX_OBSERVATIONS:
            raise ValueError(f"at most {self.MAX_OBSERVATIONS} observations may be extracted at once")

        seen: set[str] = set()
        results: list[ExtractionResult] = []
        for observation in items:
            if observation.observation_id in seen:
                raise ValueError("observation_id values must be unique in extraction batch")
            seen.add(observation.observation_id)
            results.append(self.extract(observation))
        return results


semantic_extractor = DeterministicSemanticExtractor()
