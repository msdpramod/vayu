import pytest

from app.idempotency import IdempotencyStore


def test_idempotency_round_trip(tmp_path):
    store = IdempotencyStore(str(tmp_path / "vayu.db"))
    response = {"status": "ok", "intent": "hello", "reply": "Hello", "executed": True}
    store.put("req-12345678", "hello", response)
    assert store.get("req-12345678", "hello") == response


def test_same_request_id_rejects_different_command(tmp_path):
    store = IdempotencyStore(str(tmp_path / "vayu.db"))
    store.put("req-12345678", "hello", {"status": "ok"})
    with pytest.raises(ValueError):
        store.get("req-12345678", "status")


def test_idempotency_survives_new_store_instance(tmp_path):
    db = tmp_path / "vayu.db"
    first = IdempotencyStore(str(db))
    first.put("req-12345678", "hello", {"status": "ok"})
    second = IdempotencyStore(str(db))
    assert second.get("req-12345678", "hello") == {"status": "ok"}


def test_clear_removes_cached_results(tmp_path):
    store = IdempotencyStore(str(tmp_path / "vayu.db"))
    store.put("req-12345678", "hello", {"status": "ok"})
    store.clear()
    assert store.get("req-12345678", "hello") is None
