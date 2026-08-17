import pytest

from app.payload_policy import validate_planner_payload


def test_accepts_bounded_json_payload():
    validate_planner_payload({"recipient": "user@example.com", "subject": "Hello", "metadata": {"priority": 1}})


def test_rejects_secret_or_execution_fields():
    with pytest.raises(ValueError):
        validate_planner_payload({"credentials": {"token": "never-stage-this"}})
    with pytest.raises(ValueError):
        validate_planner_payload({"shell": "rm -rf /"})


def test_rejects_excessive_depth():
    with pytest.raises(ValueError):
        validate_planner_payload({"a": {"b": {"c": {"d": {"e": "too-deep"}}}}})


def test_rejects_oversized_payload():
    with pytest.raises(ValueError):
        validate_planner_payload({"body": "x" * (8 * 1024)})
