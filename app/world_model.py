from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Iterable


MAX_ENTITY_ID = 128
MAX_ENTITY_TYPE = 64
MAX_PREDICATE = 96
MAX_VALUE = 2048
MAX_PROVENANCE = 256
MAX_QUERY_LIMIT = 100


@dataclass(frozen=True)
class WorldFact:
    id: int
    subject_id: str
    subject_type: str
    predicate: str
    value: str
    object_id: str | None
    confidence: float
    provenance: str
    observed_at: str
    valid_from: str
    valid_to: str | None
    superseded_by: int | None

    @property
    def is_current(self) -> bool:
        return self.valid_to is None and self.superseded_by is None


class WorldModel:
    """Durable, evidence-aware representation of Vayu's known world state.

    The world model stores observations and relationships only. It has no planner,
    executor, network, permission, or action authority.
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = Path(db_path or os.getenv("VAYU_DB_PATH", "data/vayu.db"))
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS world_entities (
                    entity_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS world_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    value TEXT NOT NULL,
                    object_id TEXT,
                    confidence REAL NOT NULL,
                    provenance TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_to TEXT,
                    superseded_by INTEGER,
                    FOREIGN KEY(subject_id) REFERENCES world_entities(entity_id),
                    FOREIGN KEY(object_id) REFERENCES world_entities(entity_id),
                    FOREIGN KEY(superseded_by) REFERENCES world_facts(id)
                );

                CREATE INDEX IF NOT EXISTS idx_world_facts_subject_predicate
                    ON world_facts(subject_id, predicate, id DESC);
                CREATE INDEX IF NOT EXISTS idx_world_facts_current
                    ON world_facts(subject_id, predicate, valid_to, superseded_by);
                """
            )

    @staticmethod
    def _bounded(value: str, field: str, max_len: int) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} is required")
        if len(normalized) > max_len:
            raise ValueError(f"{field} exceeds {max_len} characters")
        return normalized

    @staticmethod
    def _timestamp(value: datetime | str | None, field: str) -> str:
        if value is None:
            parsed = datetime.now(timezone.utc)
        elif isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError(f"{field} must be ISO-8601") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{field} must be timezone-aware")
        return parsed.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _confidence(value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return float(value)

    def _ensure_entity(self, connection: sqlite3.Connection, entity_id: str, entity_type: str, created_at: str) -> None:
        row = connection.execute(
            "SELECT entity_type FROM world_entities WHERE entity_id = ?",
            (entity_id,),
        ).fetchone()
        if row is None:
            connection.execute(
                "INSERT INTO world_entities(entity_id, entity_type, created_at) VALUES (?, ?, ?)",
                (entity_id, entity_type, created_at),
            )
        elif row["entity_type"] != entity_type:
            raise ValueError("entity_id already exists with a different entity_type")

    def observe(
        self,
        *,
        subject_id: str,
        subject_type: str,
        predicate: str,
        value: str,
        confidence: float,
        provenance: str,
        observed_at: datetime | str | None = None,
        object_id: str | None = None,
        object_type: str | None = None,
    ) -> WorldFact:
        subject_id = self._bounded(subject_id, "subject_id", MAX_ENTITY_ID)
        subject_type = self._bounded(subject_type, "subject_type", MAX_ENTITY_TYPE)
        predicate = self._bounded(predicate, "predicate", MAX_PREDICATE)
        value = self._bounded(value, "value", MAX_VALUE)
        provenance = self._bounded(provenance, "provenance", MAX_PROVENANCE)
        confidence = self._confidence(confidence)
        observed = self._timestamp(observed_at, "observed_at")

        if object_id is not None:
            object_id = self._bounded(object_id, "object_id", MAX_ENTITY_ID)
            if object_type is None:
                raise ValueError("object_type is required when object_id is provided")
            object_type = self._bounded(object_type, "object_type", MAX_ENTITY_TYPE)
        elif object_type is not None:
            raise ValueError("object_id is required when object_type is provided")

        with self._lock, self._connect() as connection:
            self._ensure_entity(connection, subject_id, subject_type, observed)
            if object_id is not None and object_type is not None:
                self._ensure_entity(connection, object_id, object_type, observed)

            current = connection.execute(
                """SELECT * FROM world_facts
                   WHERE subject_id = ? AND predicate = ?
                     AND valid_to IS NULL AND superseded_by IS NULL
                   ORDER BY id DESC LIMIT 1""",
                (subject_id, predicate),
            ).fetchone()

            if current is not None:
                same_claim = current["value"] == value and current["object_id"] == object_id
                if same_claim:
                    if confidence > current["confidence"]:
                        connection.execute(
                            """UPDATE world_facts
                               SET confidence = ?, provenance = ?, observed_at = ?
                               WHERE id = ?""",
                            (confidence, provenance, observed, current["id"]),
                        )
                    return self._get(connection, current["id"])

                if confidence <= current["confidence"]:
                    # Lower/equal-confidence contradiction is retained as historical evidence,
                    # but does not displace the current belief.
                    cursor = connection.execute(
                        """INSERT INTO world_facts(
                            subject_id, subject_type, predicate, value, object_id,
                            confidence, provenance, observed_at, valid_from, valid_to
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            subject_id,
                            subject_type,
                            predicate,
                            value,
                            object_id,
                            confidence,
                            provenance,
                            observed,
                            observed,
                            observed,
                        ),
                    )
                    return self._get(connection, cursor.lastrowid)

            cursor = connection.execute(
                """INSERT INTO world_facts(
                    subject_id, subject_type, predicate, value, object_id,
                    confidence, provenance, observed_at, valid_from
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    subject_id,
                    subject_type,
                    predicate,
                    value,
                    object_id,
                    confidence,
                    provenance,
                    observed,
                    observed,
                ),
            )
            new_id = int(cursor.lastrowid)

            if current is not None:
                connection.execute(
                    "UPDATE world_facts SET valid_to = ?, superseded_by = ? WHERE id = ?",
                    (observed, new_id, current["id"]),
                )

            return self._get(connection, new_id)

    def _get(self, connection: sqlite3.Connection, fact_id: int) -> WorldFact:
        row = connection.execute("SELECT * FROM world_facts WHERE id = ?", (fact_id,)).fetchone()
        if row is None:
            raise KeyError(fact_id)
        return WorldFact(**dict(row))

    def current(self, subject_id: str, predicate: str | None = None, limit: int = 20) -> list[WorldFact]:
        subject_id = self._bounded(subject_id, "subject_id", MAX_ENTITY_ID)
        safe_limit = max(1, min(int(limit), MAX_QUERY_LIMIT))
        query = """SELECT * FROM world_facts
                   WHERE subject_id = ? AND valid_to IS NULL AND superseded_by IS NULL"""
        params: list[object] = [subject_id]
        if predicate is not None:
            predicate = self._bounded(predicate, "predicate", MAX_PREDICATE)
            query += " AND predicate = ?"
            params.append(predicate)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(safe_limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [WorldFact(**dict(row)) for row in rows]

    def history(self, subject_id: str, predicate: str, limit: int = 20) -> list[WorldFact]:
        subject_id = self._bounded(subject_id, "subject_id", MAX_ENTITY_ID)
        predicate = self._bounded(predicate, "predicate", MAX_PREDICATE)
        safe_limit = max(1, min(int(limit), MAX_QUERY_LIMIT))
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM world_facts
                   WHERE subject_id = ? AND predicate = ?
                   ORDER BY id DESC LIMIT ?""",
                (subject_id, predicate, safe_limit),
            ).fetchall()
        return [WorldFact(**dict(row)) for row in rows]

    def entities(self, limit: int = 100) -> list[dict[str, str]]:
        safe_limit = max(1, min(int(limit), MAX_QUERY_LIMIT))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT entity_id, entity_type, created_at FROM world_entities ORDER BY created_at DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def clear(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM world_facts")
            connection.execute("DELETE FROM world_entities")
