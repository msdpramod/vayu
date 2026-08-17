from __future__ import annotations

import json
from typing import Any


MAX_PAYLOAD_BYTES = 8 * 1024
MAX_DEPTH = 4
MAX_COLLECTION_ITEMS = 64
FORBIDDEN_KEYS = frozenset({
    "api_key",
    "apikey",
    "credential",
    "credentials",
    "executable",
    "password",
    "script",
    "secret",
    "shell",
    "subprocess",
    "token",
})


def validate_planner_payload(payload: dict[str, Any]) -> None:
    """Fail closed on payloads that are too large, complex, secret-bearing, or executable-like."""
    if not isinstance(payload, dict):
        raise ValueError("Planner action payload must be an object.")

    def visit(value: Any, depth: int) -> None:
        if depth > MAX_DEPTH:
            raise ValueError("Planner action payload exceeds maximum nesting depth.")
        if value is None or isinstance(value, (str, int, float, bool)):
            return
        if isinstance(value, list):
            if len(value) > MAX_COLLECTION_ITEMS:
                raise ValueError("Planner action payload contains an oversized list.")
            for item in value:
                visit(item, depth + 1)
            return
        if isinstance(value, dict):
            if len(value) > MAX_COLLECTION_ITEMS:
                raise ValueError("Planner action payload contains too many fields.")
            for raw_key, item in value.items():
                if not isinstance(raw_key, str):
                    raise ValueError("Planner action payload keys must be strings.")
                key = raw_key.strip().lower().replace("-", "_")
                if key in FORBIDDEN_KEYS:
                    raise ValueError(f"Planner action payload field '{raw_key}' is forbidden.")
                visit(item, depth + 1)
            return
        raise ValueError("Planner action payload contains an unsupported value type.")

    visit(payload, 0)
    try:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("Planner action payload must be JSON serializable.") from exc
    if len(encoded) > MAX_PAYLOAD_BYTES:
        raise ValueError("Planner action payload exceeds maximum size.")
