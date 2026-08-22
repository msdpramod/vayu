from datetime import datetime, timedelta, timezone

import pytest

from app.perception import PerceptionGateway, PerceptionModality, PerceptionObservation


def observation(
    observation_id: str,
    modality: PerceptionModality,
    *,
    importance: float = 0.5,
    urgency: float = 0.5,
    novelty: float = 0.5,
    confidence: float = 0.9,
    observed_at: datetime | None = None,
) -> PerceptionObservation:
    return PerceptionObservation(
        observation_id=observation_id,
        modality=modality,
        source="test-adapter",
        summary=f"{modality.value} observation",
        observed_at=observed_at or datetime.now(timezone.utc),
        importance=importance,
        urgency=urgency,
        novelty=novelty,
        confidence=confidence,
    )


def test_multimodal_observations_feed_attention_without_action_authority():
    gateway = PerceptionGateway()
    items = [
        observation("voice-1", PerceptionModality.VOICE, importance=0.9, urgency=0.8, novelty=0.7),
        observation("vision-1", PerceptionModality.VISION, importance=0.4, urgency=0.2, novelty=0.6),
        observation("device-1", PerceptionModality.DEVICE, importance=0.5, urgency=0.4, novelty=0.5),
    ]

    decisions = gateway.attend(items, current_focus_salience=0.2, limit=3)

    assert [decision.stimulus_id for decision in decisions][0] == "voice-1"
    assert decisions[0].should_interrupt is True
    assert all(hasattr(decision, "salience") for decision in decisions)
    assert all(not hasattr(decision, "execute") for decision in decisions)


def test_duplicate_observation_ids_fail_closed():
    gateway = PerceptionGateway()
    duplicate = observation("same", PerceptionModality.FILE)

    with pytest.raises(ValueError, match="observation_id values must be unique"):
        gateway.normalize([duplicate, duplicate])


def test_future_dated_observation_fails_closed():
    gateway = PerceptionGateway()
    now = datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc)
    future = observation(
        "future",
        PerceptionModality.BROWSER,
        observed_at=now + timedelta(minutes=2),
    )

    with pytest.raises(ValueError, match="too far in the future"):
        gateway.normalize([future], now=now)


def test_naive_timestamps_are_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        observation(
            "naive",
            PerceptionModality.USER_TEXT,
            observed_at=datetime(2026, 8, 23, 0, 0),
        )


def test_batch_size_is_bounded():
    gateway = PerceptionGateway()
    items = [observation(f"obs-{index}", PerceptionModality.VISION) for index in range(65)]

    with pytest.raises(ValueError, match="at most 64 observations"):
        gateway.normalize(items)


def test_voice_and_user_text_are_user_attention_not_safety_overrides():
    gateway = PerceptionGateway()
    voice = observation(
        "voice",
        PerceptionModality.VOICE,
        importance=0.9,
        urgency=0.9,
        novelty=0.9,
        confidence=1.0,
    )

    decision = gateway.attend([voice], current_focus_salience=0.95, limit=1)[0]

    assert decision.kind.value == "user"
    assert decision.reason != "credible urgent safety signal"
