from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.credentials import CredentialProviderRegistry, MemoryCredentialProvider
from app.social_identity import SocialCredentialReference


def _setup(*, lease_seconds: int = 300):
    provider = MemoryCredentialProvider("keychain")
    provider.put(
        "social/linkedin/owner",
        b"super-secret-token",
        scopes=("social.publish", "social.read"),
    )
    registry = CredentialProviderRegistry(lease_seconds=lease_seconds)
    registry.register(provider)
    ref = SocialCredentialReference(provider="keychain", key="social/linkedin/owner")
    return provider, registry, ref


def test_metadata_inspection_is_secret_free_and_scope_aware():
    _, registry, ref = _setup()

    metadata = registry.inspect(ref, required_scopes=("social.publish",))

    assert metadata.available is True
    assert metadata.provider == "keychain"
    assert metadata.key == "social/linkedin/owner"
    assert "super-secret-token" not in repr(metadata)

    denied = registry.inspect(ref, required_scopes=("social.delete",))
    assert denied.available is False
    assert denied.detail == "required credential scope is unavailable"


def test_lease_is_short_lived_redacted_and_zeroized_on_close():
    _, registry, ref = _setup(lease_seconds=30)

    lease = registry.lease(ref, required_scopes=("social.publish",))

    assert lease.reveal("social.publish") == b"super-secret-token"
    assert "super-secret-token" not in repr(lease)
    assert lease.expires_at <= datetime.now(timezone.utc) + timedelta(seconds=31)

    lease.close()
    assert lease.closed is True
    with pytest.raises(RuntimeError, match="closed"):
        lease.reveal("social.publish")


def test_context_manager_closes_credential_lease():
    _, registry, ref = _setup()

    with registry.lease(ref, required_scopes=("social.read",)) as lease:
        assert lease.reveal("social.read") == b"super-secret-token"

    assert lease.closed is True


def test_missing_scope_fails_closed_before_secret_resolution():
    provider, registry, ref = _setup()
    original_resolve = provider.resolve
    calls = 0

    def counting_resolve(key):
        nonlocal calls
        calls += 1
        return original_resolve(key)

    provider.resolve = counting_resolve

    with pytest.raises(PermissionError, match="scope"):
        registry.lease(ref, required_scopes=("social.delete",))
    assert calls == 0


def test_expired_credential_fails_closed_without_lease():
    provider = MemoryCredentialProvider("vault")
    provider.put(
        "linkedin/owner",
        b"expired-token",
        scopes=("social.publish",),
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    registry = CredentialProviderRegistry()
    registry.register(provider)
    ref = SocialCredentialReference(provider="vault", key="linkedin/owner")

    metadata = registry.inspect(ref, required_scopes=("social.publish",))
    assert metadata.available is False
    assert metadata.detail == "credential expired"
    with pytest.raises(PermissionError, match="expired"):
        registry.lease(ref, required_scopes=("social.publish",))


def test_provider_registration_and_lookup_fail_closed():
    provider, registry, _ = _setup()

    with pytest.raises(ValueError, match="already registered"):
        registry.register(provider)

    missing = SocialCredentialReference(provider="vault", key="social/linkedin/owner")
    with pytest.raises(LookupError, match="not registered"):
        registry.inspect(missing)


def test_lease_duration_is_bounded():
    with pytest.raises(ValueError, match="between 1 and 900"):
        CredentialProviderRegistry(lease_seconds=901)


def test_provider_expiry_caps_lease_expiry():
    expiry = datetime.now(timezone.utc) + timedelta(seconds=20)
    provider = MemoryCredentialProvider("vault")
    provider.put(
        "linkedin/owner",
        b"short-token",
        scopes=("social.publish",),
        expires_at=expiry,
    )
    registry = CredentialProviderRegistry(lease_seconds=300)
    registry.register(provider)
    ref = SocialCredentialReference(provider="vault", key="linkedin/owner")

    lease = registry.lease(ref, required_scopes=("social.publish",))
    assert lease.expires_at == expiry
