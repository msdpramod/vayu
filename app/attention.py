from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Iterable


class StimulusKind(str, Enum):
    USER = "user"
    SYSTEM = "system"
    REMINDER = "reminder"
    PERCEPTION = "perception"
    SAFETY = "safety"


@dataclass(frozen=True)
class AttentionStimulus:
    """A bounded piece of information competing for Vayu's current focus.

    Scores are caller-supplied evidence in [0, 1]. The controller only ranks
    and selects attention; it has no authority to execute actions or modify state.
    """

    stimulus_id: str
    kind: StimulusKind
    summary: str
    importance: float
    urgency: float
    novelty: float
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.stimulus_id.strip():
            raise ValueError("stimulus_id is required")
        if not self.summary.strip():
            raise ValueError("summary is required")
        if len(self.summary) > 500:
            raise ValueError("summary must be at most 500 characters")
        for field_name in ("importance", "urgency", "novelty", "confidence"):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")


@dataclass(frozen=True)
class AttentionDecision:
    stimulus_id: str
    kind: StimulusKind
    summary: str
    salience: float
    should_interrupt: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class AttentionController:
    """Deterministic salience and interruption policy for Vayu.

    The controller is intentionally pure and bounded. It does not call models,
    tools, executors, networks, or persistence. This keeps perception and future
    multimodal inputs from gaining action authority merely by becoming salient.
    """

    MAX_STIMULI = 64

    def __init__(self, interrupt_threshold: float = 0.78, interrupt_margin: float = 0.12):
        if not 0.0 <= interrupt_threshold <= 1.0:
            raise ValueError("interrupt_threshold must be between 0 and 1")
        if not 0.0 <= interrupt_margin <= 1.0:
            raise ValueError("interrupt_margin must be between 0 and 1")
        self.interrupt_threshold = interrupt_threshold
        self.interrupt_margin = interrupt_margin

    @staticmethod
    def salience(stimulus: AttentionStimulus) -> float:
        # Urgency and importance dominate; novelty helps surface change, while
        # confidence prevents uncertain novelty from hijacking attention.
        raw = (
            0.36 * stimulus.importance
            + 0.36 * stimulus.urgency
            + 0.18 * stimulus.novelty
            + 0.10 * stimulus.confidence
        )

        # Safety signals receive a narrow boost, not an automatic maximum score.
        # They still need meaningful evidence, but credible hazards surface early.
        if stimulus.kind == StimulusKind.SAFETY:
            raw += 0.08 * stimulus.confidence

        return round(min(raw, 1.0), 4)

    def rank(self, stimuli: Iterable[AttentionStimulus]) -> list[tuple[AttentionStimulus, float]]:
        items = list(stimuli)
        if len(items) > self.MAX_STIMULI:
            raise ValueError(f"at most {self.MAX_STIMULI} stimuli may be ranked at once")
        seen: set[str] = set()
        for item in items:
            if item.stimulus_id in seen:
                raise ValueError("stimulus_id values must be unique")
            seen.add(item.stimulus_id)

        scored = [(item, self.salience(item)) for item in items]
        # Deterministic tie-breaker avoids unstable focus changes across runs.
        return sorted(scored, key=lambda pair: (-pair[1], pair[0].stimulus_id))

    def select(
        self,
        stimuli: Iterable[AttentionStimulus],
        *,
        current_focus_salience: float = 0.0,
        limit: int = 3,
    ) -> list[AttentionDecision]:
        if not 0.0 <= current_focus_salience <= 1.0:
            raise ValueError("current_focus_salience must be between 0 and 1")
        if not 1 <= limit <= 10:
            raise ValueError("limit must be between 1 and 10")

        decisions: list[AttentionDecision] = []
        for stimulus, score in self.rank(stimuli)[:limit]:
            strong_enough = score >= self.interrupt_threshold
            exceeds_focus = score >= min(1.0, current_focus_salience + self.interrupt_margin)
            safety_override = (
                stimulus.kind == StimulusKind.SAFETY
                and stimulus.confidence >= 0.8
                and stimulus.urgency >= 0.8
            )
            should_interrupt = safety_override or (strong_enough and exceeds_focus)

            if safety_override:
                reason = "credible urgent safety signal"
            elif should_interrupt:
                reason = "salience exceeds interruption threshold and current focus"
            elif score < self.interrupt_threshold:
                reason = "salience below interruption threshold"
            else:
                reason = "current focus remains more salient"

            decisions.append(
                AttentionDecision(
                    stimulus_id=stimulus.stimulus_id,
                    kind=stimulus.kind,
                    summary=stimulus.summary,
                    salience=score,
                    should_interrupt=should_interrupt,
                    reason=reason,
                )
            )
        return decisions


attention = AttentionController()
