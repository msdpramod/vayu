from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable


class CognitiveDomain(str, Enum):
    EXECUTIVE = "executive"
    MEMORY = "memory"
    REASONING = "reasoning"
    ATTENTION = "attention"
    WORLD_MODEL = "world_model"
    SKILLS = "skills"
    SAFETY = "safety"
    PERCEPTION = "perception"


@dataclass(frozen=True)
class CapabilitySignal:
    domain: CognitiveDomain
    name: str
    score: float
    evidence: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")
        if not self.name.strip() or not self.evidence.strip():
            raise ValueError("name and evidence are required")


@dataclass(frozen=True)
class EvolutionProposal:
    domain: CognitiveDomain
    objective: str
    reason: str
    priority: float
    created_at: str
    requires_human_review: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class EvolutionEngine:
    """Evaluates Vayu's cognitive capability signals and proposes the next improvement.

    This engine is deliberately proposal-only. It never changes code, configuration,
    permissions, prompts, tools, models, or external systems by itself.
    """

    def __init__(self, target_score: float = 0.85):
        if not 0.0 < target_score <= 1.0:
            raise ValueError("target_score must be between 0 and 1")
        self.target_score = target_score

    def domain_scores(self, signals: Iterable[CapabilitySignal]) -> dict[CognitiveDomain, float]:
        grouped: dict[CognitiveDomain, list[float]] = {}
        for signal in signals:
            grouped.setdefault(signal.domain, []).append(signal.score)
        return {domain: round(sum(values) / len(values), 4) for domain, values in grouped.items()}

    def weakest_domain(self, signals: Iterable[CapabilitySignal]) -> CognitiveDomain | None:
        scores = self.domain_scores(signals)
        if not scores:
            return None
        return min(scores, key=scores.get)

    def propose_next(self, signals: Iterable[CapabilitySignal]) -> EvolutionProposal | None:
        scores = self.domain_scores(signals)
        if not scores:
            return None
        domain = min(scores, key=scores.get)
        score = scores[domain]
        if score >= self.target_score:
            return None
        gap = self.target_score - score
        return EvolutionProposal(
            domain=domain,
            objective=f"Improve {domain.value} capability toward {self.target_score:.2f}",
            reason=f"Measured score {score:.2f} is the largest current cognitive gap.",
            priority=round(gap, 4),
            created_at=datetime.now(timezone.utc).isoformat(),
            requires_human_review=True,
        )


def baseline_signals() -> list[CapabilitySignal]:
    """Conservative baseline derived from capabilities already present in Vayu."""
    return [
        CapabilitySignal(CognitiveDomain.SAFETY, "human approval gate", 0.88, "time-bounded approval lifecycle and fail-closed execution"),
        CapabilitySignal(CognitiveDomain.MEMORY, "durable memory", 0.55, "SQLite-backed persistence exists but consolidation/semantic recall are limited"),
        CapabilitySignal(CognitiveDomain.REASONING, "bounded alternative-future simulation", 0.64, "plans are independently critiqued, checked against bounded current-world snapshots, and projected into explicit success/failure/ambiguous counterfactual futures without persisting imagined state; multi-step causal search and alternative-plan comparison remain limited"),
        CapabilitySignal(CognitiveDomain.EXECUTIVE, "goal control", 0.42, "action orchestration exists but hierarchical goals and long-horizon planning are limited"),
        CapabilitySignal(CognitiveDomain.ATTENTION, "salience controller", 0.42, "bounded deterministic salience ranking receives normalized perception evidence; durable attentional context is still pending"),
        CapabilitySignal(CognitiveDomain.WORLD_MODEL, "evidence-aware grounded state graph with counterfactual overlays", 0.45, "durable temporal facts support confidence/provenance-aware grounding plus immutable bounded current-state snapshots and non-persistent predicted deltas; richer relationships and learned predictive transitions remain limited"),
        CapabilitySignal(CognitiveDomain.SKILLS, "skill registry", 0.52, "explicit skills exist without learned success/latency scoring"),
        CapabilitySignal(CognitiveDomain.PERCEPTION, "bounded sensory semantics with deterministic extraction", 0.44, "device/browser/file observations can be deterministically extracted through exact allow-listed patterns before semantic validation and critique; live adapters and general extraction remain absent"),
    ]
