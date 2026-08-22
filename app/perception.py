from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Iterable

from app.attention import AttentionController, AttentionDecision, AttentionStimulus, StimulusKind


class PerceptionModality(str, Enum):
    USER_TEXT = "user_text"
    VOICE = "voice"
    VISION = "vision"
    BROWSER = "browser"
    DEVICE = "device"
    FILE = "file"


@dataclass(frozen=True)
class PerceptionObservation:
    """A normalized, bounded observation from a sensory/input adapter.

    Observations contain evidence only. They cannot encode executable callbacks,
    tools, permissions, credentials, or action authority.
    """

    observation_id: str
    modality: PerceptionModality
    source: str
    summary: str
    observed_at: datetime
    importance: float
    urgency: float
    novelty: float
    confidence: float

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("observation_id is required")
        if len(self.observation_id) > 128:
            raise ValueError("observation_id must be at most 128 characters")
        if not self.source.strip():
            raise ValueError("source is required")
        if len(self.source) > 128:
            raise ValueError("source must be at most 128 characters")
        if not self.summary.strip():
            raise ValueError("summary is required")
        if len(self.summary) > 500:
            raise ValueError("summary must be at most 500 characters")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        for field_name in ("importance", "urgency", "novelty", "confidence"):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")


@dataclass(frozen=True)
class PerceptionResult:
    observation: PerceptionObservation
    attention: AttentionDecision


class PerceptionGateway:
    """Normalizes sensory evidence into Vayu's attention boundary.

    This gateway deliberately has no references to executors, planners, action
    stores, permissions, networks, models, or mutable application state. Sensor
    adapters may submit bounded observations; the only output is an attention
    recommendation.
    """

    MAX_OBSERVATIONS = 64
    MAX_FUTURE_SKEW = timedelta(seconds=60)

    def __init__(self, attention_controller: AttentionController | None = None):
        self.attention_controller = attention_controller or AttentionController()

    @staticmethod
    def _stimulus_kind(observation: PerceptionObservation) -> StimulusKind:
        if observation.modality in (PerceptionModality.USER_TEXT, PerceptionModality.VOICE):
            return StimulusKind.USER
        return StimulusKind.PERCEPTION

    def normalize(
        self,
        observations: Iterable[PerceptionObservation],
        *,
        now: datetime | None = None,
    ) -> list[AttentionStimulus]:
        items = list(observations)
        if len(items) > self.MAX_OBSERVATIONS:
            raise ValueError(f"at most {self.MAX_OBSERVATIONS} observations may be normalized at once")

        reference = now or datetime.now(timezone.utc)
        if reference.tzinfo is None or reference.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        seen: set[str] = set()
        stimuli: list[AttentionStimulus] = []
        for observation in items:
            if observation.observation_id in seen:
                raise ValueError("observation_id values must be unique")
            seen.add(observation.observation_id)

            observed_at = observation.observed_at.astimezone(timezone.utc)
            if observed_at > reference.astimezone(timezone.utc) + self.MAX_FUTURE_SKEW:
                raise ValueError("observed_at is too far in the future")

            stimuli.append(
                AttentionStimulus(
                    stimulus_id=observation.observation_id,
                    kind=self._stimulus_kind(observation),
                    summary=observation.summary,
                    importance=observation.importance,
                    urgency=observation.urgency,
                    novelty=observation.novelty,
                    confidence=observation.confidence,
                )
            )
        return stimuli

    def attend(
        self,
        observations: Iterable[PerceptionObservation],
        *,
        current_focus_salience: float = 0.0,
        limit: int = 3,
        now: datetime | None = None,
    ) -> list[AttentionDecision]:
        stimuli = self.normalize(observations, now=now)
        return self.attention_controller.select(
            stimuli,
            current_focus_salience=current_focus_salience,
            limit=limit,
        )


perception = PerceptionGateway()
