from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Protocol


_PROVIDER_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
_MAX_SCOPES = 32
_DEFAULT_LEASE_SECONDS = 300
_MAX_LEASE_SECONDS = 900


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _bounded(value: str, field: str, limit: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} is required")
    if len(normalized) > limit:
        raise ValueError(f"{field} exceeds {limit} characters")
    return normalized


def _validate_scopes(scopes: tuple[str, ...]) -> tuple[str, ...]:
    if len(scopes) > _MAX_SCOPES:
        raise ValueError(f"credential scopes are bounded to {_MAX_SCOPES}")
    normalized = tuple(_bounded(scope, "scope", 120) for scope in scopes)
    if len(set(normalized)) != len(normalized):
        raise ValueError("credential scopes must not contain duplicates")
    return normalized


class CredentialLocator(Protocol):
    provider: str
    key: str


@dataclass(frozen=True)
class CredentialMetadata:
    provider: str
    key: str
    scopes: tuple[str, ...]
    expires_at: datetime | None
    available: bool
    detail: str

    def __post_init__(self) -> None:
        if not _PROVIDER_RE.fullmatch(self.provider):
            raise ValueError("credential provider id is invalid")
        _bounded(self.key, "credential key", 200)
        _validate_scopes(self.scopes)
        _bounded(self.detail, "credential detail", 500)
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("credential expiry must be timezone-aware")


@dataclass(frozen=True)
class ProviderCredential:
    """Provider-only resolution result. Never persist or log this object."""

    secret: bytes
    scopes: tuple[str, ...]
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.secret, bytes) or not self.secret:
            raise ValueError("resolved credential secret must be non-empty bytes")
        _validate_scopes(self.scopes)
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("credential expiry must be timezone-aware")


class CredentialProvider(Protocol):
    provider_id: str

    def inspect(self, key: str) -> CredentialMetadata: ...

    def resolve(self, key: str) -> ProviderCredential: ...


class CredentialLease:
    """Short-lived in-memory credential material with explicit scope checks.

    The lease deliberately has no JSON/dataclass serializer. Its representation is
    redacted, and ``close`` performs best-effort zeroization of the local byte buffer.
    """

    __slots__ = ("provider", "key", "scopes", "expires_at", "_secret", "_closed")

    def __init__(
        self,
        *,
        provider: str,
        key: str,
        secret: bytes,
        scopes: tuple[str, ...],
        expires_at: datetime,
    ) -> None:
        self.provider = provider
        self.key = key
        self.scopes = _validate_scopes(scopes)
        if expires_at.tzinfo is None:
            raise ValueError("lease expiry must be timezone-aware")
        self.expires_at = expires_at
        self._secret = bytearray(secret)
        self._closed = False

    def __repr__(self) -> str:
        return (
            f"CredentialLease(provider={self.provider!r}, key={self.key!r}, "
            f"scopes={self.scopes!r}, expires_at={self.expires_at.isoformat()!r}, secret=<redacted>)"
        )

    @property
    def closed(self) -> bool:
        return self._closed

    def reveal(self, required_scope: str | None = None) -> bytes:
        if self._closed:
            raise RuntimeError("credential lease is closed")
        if _utc_now() >= self.expires_at:
            self.close()
            raise PermissionError("credential lease expired")
        if required_scope is not None and required_scope not in self.scopes:
            raise PermissionError("credential lease does not grant the required scope")
        return bytes(self._secret)

    def close(self) -> None:
        if self._closed:
            return
        for index in range(len(self._secret)):
            self._secret[index] = 0
        self._closed = True

    def __enter__(self) -> CredentialLease:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class CredentialProviderRegistry:
    """Provider-neutral credential cortex for Vayu organs.

    Durable code stores only provider/key locators. Secret material is resolved only
    on demand into a bounded in-memory lease and is never returned by ``inspect``.
    """

    def __init__(self, *, lease_seconds: int = _DEFAULT_LEASE_SECONDS) -> None:
        if not 1 <= lease_seconds <= _MAX_LEASE_SECONDS:
            raise ValueError(f"lease_seconds must be between 1 and {_MAX_LEASE_SECONDS}")
        self.lease_seconds = lease_seconds
        self._providers: dict[str, CredentialProvider] = {}

    def register(self, provider: CredentialProvider) -> None:
        provider_id = provider.provider_id
        if not _PROVIDER_RE.fullmatch(provider_id):
            raise ValueError("credential provider id is invalid")
        if provider_id in self._providers:
            raise ValueError(f"credential provider '{provider_id}' is already registered")
        self._providers[provider_id] = provider

    def _provider(self, locator: CredentialLocator) -> CredentialProvider:
        if not _PROVIDER_RE.fullmatch(locator.provider):
            raise ValueError("credential provider id is invalid")
        _bounded(locator.key, "credential key", 200)
        provider = self._providers.get(locator.provider)
        if provider is None:
            raise LookupError(f"credential provider '{locator.provider}' is not registered")
        return provider

    def inspect(
        self,
        locator: CredentialLocator,
        *,
        required_scopes: tuple[str, ...] = (),
    ) -> CredentialMetadata:
        required = _validate_scopes(required_scopes)
        metadata = self._provider(locator).inspect(locator.key)
        if metadata.provider != locator.provider or metadata.key != locator.key:
            raise RuntimeError("credential provider returned mismatched metadata")
        if metadata.expires_at is not None and metadata.expires_at <= _utc_now():
            return CredentialMetadata(
                provider=metadata.provider,
                key=metadata.key,
                scopes=metadata.scopes,
                expires_at=metadata.expires_at,
                available=False,
                detail="credential expired",
            )
        if not set(required).issubset(metadata.scopes):
            return CredentialMetadata(
                provider=metadata.provider,
                key=metadata.key,
                scopes=metadata.scopes,
                expires_at=metadata.expires_at,
                available=False,
                detail="required credential scope is unavailable",
            )
        return metadata

    def lease(
        self,
        locator: CredentialLocator,
        *,
        required_scopes: tuple[str, ...] = (),
    ) -> CredentialLease:
        required = _validate_scopes(required_scopes)
        metadata = self.inspect(locator, required_scopes=required)
        if not metadata.available:
            raise PermissionError(metadata.detail)

        resolved = self._provider(locator).resolve(locator.key)
        if not set(required).issubset(resolved.scopes):
            raise PermissionError("resolved credential does not grant the required scope")
        now = _utc_now()
        if resolved.expires_at is not None and resolved.expires_at <= now:
            raise PermissionError("resolved credential expired")
        lease_expiry = now + timedelta(seconds=self.lease_seconds)
        if resolved.expires_at is not None:
            lease_expiry = min(lease_expiry, resolved.expires_at)
        return CredentialLease(
            provider=locator.provider,
            key=locator.key,
            secret=resolved.secret,
            scopes=resolved.scopes,
            expires_at=lease_expiry,
        )


class MemoryCredentialProvider:
    """Deterministic process-local provider for tests and development.

    This is intentionally not a durable secret store. Production runtimes should
    implement the same provider contract for OS keychains or managed secret stores.
    """

    def __init__(self, provider_id: str = "memory") -> None:
        if not _PROVIDER_RE.fullmatch(provider_id):
            raise ValueError("credential provider id is invalid")
        self.provider_id = provider_id
        self._values: dict[str, ProviderCredential] = {}

    def put(
        self,
        key: str,
        secret: bytes,
        *,
        scopes: tuple[str, ...],
        expires_at: datetime | None = None,
    ) -> None:
        normalized_key = _bounded(key, "credential key", 200)
        self._values[normalized_key] = ProviderCredential(
            secret=secret,
            scopes=scopes,
            expires_at=expires_at,
        )

    def inspect(self, key: str) -> CredentialMetadata:
        normalized_key = _bounded(key, "credential key", 200)
        credential = self._values.get(normalized_key)
        if credential is None:
            return CredentialMetadata(
                provider=self.provider_id,
                key=normalized_key,
                scopes=(),
                expires_at=None,
                available=False,
                detail="credential not found",
            )
        return CredentialMetadata(
            provider=self.provider_id,
            key=normalized_key,
            scopes=credential.scopes,
            expires_at=credential.expires_at,
            available=True,
            detail="credential metadata available",
        )

    def resolve(self, key: str) -> ProviderCredential:
        normalized_key = _bounded(key, "credential key", 200)
        credential = self._values.get(normalized_key)
        if credential is None:
            raise LookupError("credential not found")
        return credential
