from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sqlite3
from threading import Lock


_PROVIDER_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
_KEY_RE = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SocialCredentialReference:
    """Non-secret locator for credential material held outside Vayu's database.

    The reference deliberately cannot contain URI schemes, whitespace, query strings,
    bearer tokens, cookies, or arbitrary serialized credential material. A future
    credential provider resolves ``provider`` + ``key`` out of band.
    """

    provider: str
    key: str

    def __post_init__(self) -> None:
        if not _PROVIDER_RE.fullmatch(self.provider):
            raise ValueError("credential provider must be a bounded logical provider id")
        if not _KEY_RE.fullmatch(self.key):
            raise ValueError("credential key must be a bounded non-secret locator")


@dataclass(frozen=True)
class DurableSocialBinding:
    platform: str
    account_id: str
    adapter_id: str
    credential_ref: SocialCredentialReference | None
    revision: int
    enabled: bool
    created_at: str
    updated_at: str
    revoked_at: str | None


class SocialAccountStore:
    """Durable social account identity state without OAuth material.

    Only platform/account/adapter identity and an optional non-secret credential
    locator are persisted. Raw OAuth tokens, refresh tokens, passwords and cookies
    have no storage field in this schema.
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = Path(db_path or os.getenv("VAYU_DB_PATH", "data/vayu.db"))
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS social_account_bindings (
                    platform TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    adapter_id TEXT NOT NULL,
                    credential_provider TEXT,
                    credential_key TEXT,
                    revision INTEGER NOT NULL,
                    enabled INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    revoked_at TEXT,
                    PRIMARY KEY(platform, account_id)
                );

                CREATE INDEX IF NOT EXISTS idx_social_account_bindings_enabled
                    ON social_account_bindings(enabled, platform, account_id);
                """
            )

    @staticmethod
    def _decode(row: sqlite3.Row) -> DurableSocialBinding:
        provider = row["credential_provider"]
        key = row["credential_key"]
        credential_ref = (
            SocialCredentialReference(provider=provider, key=key)
            if provider is not None and key is not None
            else None
        )
        return DurableSocialBinding(
            platform=row["platform"],
            account_id=row["account_id"],
            adapter_id=row["adapter_id"],
            credential_ref=credential_ref,
            revision=int(row["revision"]),
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            revoked_at=row["revoked_at"],
        )

    def get(self, platform: str, account_id: str) -> DurableSocialBinding | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM social_account_bindings WHERE platform = ? AND account_id = ?",
                (platform, account_id),
            ).fetchone()
        return self._decode(row) if row is not None else None

    def bind(
        self,
        *,
        platform: str,
        account_id: str,
        adapter_id: str,
        credential_ref: SocialCredentialReference | None = None,
    ) -> DurableSocialBinding:
        now = _utc_now()
        with self._lock, self._connect() as connection:
            current_row = connection.execute(
                "SELECT * FROM social_account_bindings WHERE platform = ? AND account_id = ?",
                (platform, account_id),
            ).fetchone()
            current = self._decode(current_row) if current_row is not None else None

            if current is not None and current.enabled:
                same_identity = (
                    current.adapter_id == adapter_id
                    and current.credential_ref == credential_ref
                )
                if not same_identity:
                    raise PermissionError("revoke the existing social binding before changing identity")
                return current

            revision = 1 if current is None else current.revision + 1
            created_at = now if current is None else current.created_at
            provider = credential_ref.provider if credential_ref is not None else None
            key = credential_ref.key if credential_ref is not None else None
            connection.execute(
                """
                INSERT INTO social_account_bindings(
                    platform, account_id, adapter_id, credential_provider, credential_key,
                    revision, enabled, created_at, updated_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, NULL)
                ON CONFLICT(platform, account_id) DO UPDATE SET
                    adapter_id = excluded.adapter_id,
                    credential_provider = excluded.credential_provider,
                    credential_key = excluded.credential_key,
                    revision = excluded.revision,
                    enabled = 1,
                    updated_at = excluded.updated_at,
                    revoked_at = NULL
                """,
                (
                    platform,
                    account_id,
                    adapter_id,
                    provider,
                    key,
                    revision,
                    created_at,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM social_account_bindings WHERE platform = ? AND account_id = ?",
                (platform, account_id),
            ).fetchone()
        assert row is not None
        return self._decode(row)

    def revoke(self, platform: str, account_id: str) -> DurableSocialBinding | None:
        now = _utc_now()
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM social_account_bindings WHERE platform = ? AND account_id = ?",
                (platform, account_id),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """
                UPDATE social_account_bindings
                SET enabled = 0, updated_at = ?, revoked_at = ?
                WHERE platform = ? AND account_id = ?
                """,
                (now, now, platform, account_id),
            )
            updated = connection.execute(
                "SELECT * FROM social_account_bindings WHERE platform = ? AND account_id = ?",
                (platform, account_id),
            ).fetchone()
        assert updated is not None
        return self._decode(updated)
