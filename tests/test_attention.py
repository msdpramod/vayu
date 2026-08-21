import pytest

from app.attention import AttentionController, AttentionStimulus, StimulusKind


def stimulus(stimulus_id: str, **overrides):
    values = {
        "kind": StimulusKind.PERCEPTION,
        "summary": stimulus_id,
        "importance": 0.5,
        "urgency": 0.5,
        "novelty": 0.5,
        "confidence": 1.0,
    }
    values.update(overrides)
    return AttentionStimulus(stimulus_id=stimulus_id, **values)


def test_rejects_invalid_stimulus_score():
    with pytest.raises(ValueError):
        stimulus("bad", urgency=1.1)


def test_ranking_is_deterministic_and_salience_driven():
    controller = AttentionController()
    ranked = controller.rank(
        [
            stimulus("routine", importance=0.3, urgency=0.2, novelty=0.2),
            stimulus("urgent", importance=0.9, urgency=0.9, novelty=0.4),
            stimulus("medium", importance=0.5, urgency=0.6, novelty=0.5),
        ]
    )
    assert [item.stimulus_id for item, _ in ranked] == ["urgent", "medium", "routine"]


def test_uncertain_novelty_does_not_hijack_attention():
    controller = AttentionController()
    ranked = controller.rank(
        [
            stimulus("flashy", importance=0.2, urgency=0.2, novelty=1.0, confidence=0.1),
            stimulus("important", importance=0.8, urgency=0.6, novelty=0.2, confidence=0.9),
        ]
    )
    assert ranked[0][0].stimulus_id == "important"


def test_ordinary_signal_does_not_interrupt_stronger_current_focus():
    controller = AttentionController(interrupt_threshold=0.70, interrupt_margin=0.10)
    decision = controller.select(
        [stimulus("candidate", importance=0.9, urgency=0.8, novelty=0.5)],
        current_focus_salience=0.85,
        limit=1,
    )[0]
    assert decision.salience >= 0.70
    assert decision.should_interrupt is False
    assert decision.reason == "current focus remains more salient"


def test_credible_urgent_safety_signal_can_interrupt():
    controller = AttentionController()
    decision = controller.select(
        [
            stimulus(
                "hazard",
                kind=StimulusKind.SAFETY,
                importance=0.7,
                urgency=0.95,
                novelty=0.4,
                confidence=0.9,
            )
        ],
        current_focus_salience=0.95,
        limit=1,
    )[0]
    assert decision.should_interrupt is True
    assert decision.reason == "credible urgent safety signal"


def test_low_confidence_safety_signal_has_no_override():
    controller = AttentionController()
    decision = controller.select(
        [
            stimulus(
                "uncertain-hazard",
                kind=StimulusKind.SAFETY,
                importance=0.7,
                urgency=0.95,
                novelty=0.4,
                confidence=0.4,
            )
        ],
        current_focus_salience=0.95,
        limit=1,
    )[0]
    assert decision.should_interrupt is False


def test_controller_bounds_batch_size_and_rejects_duplicate_ids():
    controller = AttentionController()
    with pytest.raises(ValueError):
        controller.rank([stimulus("same"), stimulus("same")])

    with pytest.raises(ValueError):
        controller.rank([stimulus(str(index)) for index in range(controller.MAX_STIMULI + 1)])
