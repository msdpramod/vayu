from datetime import datetime, timezone

import pytest

from app.attention import AttentionController
from app.critic import CriticDisposition, SemanticCritic
from app.perception import PerceptionModality, PerceptionObservation
from app.semantic_extractor import DeterministicSemanticExtractor
from app.semantics import SemanticUnderstandingBoundary


def observation(
    observation_id: str,
    modality: PerceptionModality,
    summary: str,
    *,
    confidence: float = 0.9,
) -> PerceptionObservation:
    return PerceptionObservation(
        observation_id=observation_id,
        modality=modality,
        source="test-adapter",
        summary=summary,
        observed_at=datetime.now(timezone.utc),
        importance=0.8,
        urgency=0.5,
        novelty=0.6,
        confidence=confidence,
    )


def attention_for(obs: PerceptionObservation):
    controller = AttentionController()
    stimulus = controller.select(
        [
            __import__("app.perception", fromlist=["PerceptionGateway"])
            .PerceptionGateway(controller)
            .normalize([obs])[0]
        ],
        limit=1,
    )[0]
    return stimulus


def test_extracts_supported_device_status_without_boosting_confidence():
    extractor = DeterministicSemanticExtractor()
    obs = observation("obs-1", PerceptionModality.DEVICE, "service api is degraded", confidence=0.73)

    result = extractor.extract(obs)

    assert result.extracted is True
    assert result.frame is not None
    assert result.frame.schema == "device.service_status.v1"
    assert result.frame.subject_id == "api"
    assert result.frame.predicate == "status"
    assert result.frame.value == "degraded"
    assert result.frame.confidence == 0.73
    assert result.frame.evidence_span == "service api is degraded"


def test_extracts_browser_and_file_shapes():
    extractor = DeterministicSemanticExtractor()

    browser = extractor.extract(observation("b", PerceptionModality.BROWSER, "page checkout is ready"))
    file_result = extractor.extract(observation("f", PerceptionModality.FILE, "file config.yaml was modified"))

    assert browser.extracted and browser.frame is not None
    assert browser.frame.schema == "browser.page_state.v1"
    assert browser.frame.subject_id == "checkout"
    assert browser.frame.value == "ready"

    assert file_result.extracted and file_result.frame is not None
    assert file_result.frame.schema == "file.lifecycle.v1"
    assert file_result.frame.subject_id == "config.yaml"
    assert file_result.frame.value == "modified"


def test_abstains_on_ambiguous_or_extra_text():
    extractor = DeterministicSemanticExtractor()
    obs = observation(
        "obs-2",
        PerceptionModality.DEVICE,
        "service api is healthy but database looks down",
    )

    result = extractor.extract(obs)

    assert result.extracted is False
    assert result.frame is None


def test_abstains_for_unsupported_modality():
    extractor = DeterministicSemanticExtractor()
    obs = observation("obs-3", PerceptionModality.USER_TEXT, "service api is healthy")

    result = extractor.extract(obs)

    assert result.extracted is False
    assert "no deterministic semantic extractor" in result.reason


def test_batch_rejects_duplicate_observation_ids():
    extractor = DeterministicSemanticExtractor()
    first = observation("same", PerceptionModality.DEVICE, "service api is healthy")
    second = observation("same", PerceptionModality.FILE, "file a.txt was created")

    with pytest.raises(ValueError, match="unique"):
        extractor.extract_batch([first, second])


def test_batch_is_bounded():
    extractor = DeterministicSemanticExtractor()
    observations = [
        observation(str(index), PerceptionModality.DEVICE, f"service svc-{index} is healthy")
        for index in range(extractor.MAX_OBSERVATIONS + 1)
    ]

    with pytest.raises(ValueError, match="at most"):
        extractor.extract_batch(observations)


def test_deterministic_output_survives_semantic_boundary_and_critic():
    extractor = DeterministicSemanticExtractor()
    boundary = SemanticUnderstandingBoundary()
    critic = SemanticCritic()
    obs = observation("obs-4", PerceptionModality.DEVICE, "service payments is healthy", confidence=0.82)

    extracted = extractor.extract(obs)
    assert extracted.frame is not None

    attention = attention_for(obs)
    semantic = boundary.interpret(observation=obs, attention=attention, frame=extracted.frame)
    verdict = critic.verify(observation=obs, semantic=semantic, world_context=[])

    assert semantic.accepted is True
    assert semantic.candidate is not None
    assert semantic.candidate.confidence == 0.82
    assert verdict.disposition is CriticDisposition.VERIFIED
    assert verdict.accepted is True


def test_low_confidence_deterministic_match_still_abstains_at_semantic_boundary():
    extractor = DeterministicSemanticExtractor()
    boundary = SemanticUnderstandingBoundary(minimum_confidence=0.55)
    obs = observation("obs-5", PerceptionModality.DEVICE, "service api is healthy", confidence=0.3)

    extracted = extractor.extract(obs)
    assert extracted.extracted is True
    assert extracted.frame is not None

    semantic = boundary.interpret(
        observation=obs,
        attention=attention_for(obs),
        frame=extracted.frame,
    )

    assert semantic.accepted is False
    assert semantic.candidate is None
    assert "confidence" in semantic.reason
