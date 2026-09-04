from __future__ import annotations

import pytest

from app.actions import ActionExecutorRegistry, ProposedActionStore
from app.credentials import CredentialLease, CredentialProviderRegistry, MemoryCredentialProvider
from app.social import MockSocialAdapter, SocialAccountBinding, SocialMediaOrgan, SocialPlatform
from app.social_identity import SocialCredentialReference


class _CountingCredentialProvider(MemoryCredentialProvider):
    def __init__(self) -> None:
        super().__init__("memory")
        self.resolve_calls = 0

    def resolve(self, key: str):
        self.resolve_calls += 1
        return super().resolve(key)


class _CredentialedLinkedInAdapter(MockSocialAdapter):
    def __init__(self, *, fail_publish: bool = False) -> None:
        super().__init__(adapter_id="mock.linkedin.credentialed")
        self.fail_publish = fail_publish
        self.seen_lease: CredentialLease | None = None

    def credential_scopes(self, account_id: str) -> tuple[str, ...]:
        super().credential_scopes(account_id)
        return ("w_member_social",)

    def publish_with_credential(self, request, credential: CredentialLease):
        self.seen_lease = credential
        assert credential.reveal("w_member_social") == b"short-lived-linkedin-token"
        if self.fail_publish:
            raise RuntimeError("simulated provider failure")
        return super().publish(request)


def _credentialed_organ(tmp_path, *, scopes=("w_member_social",), bind_credential=True, fail_publish=False):
    store = ProposedActionStore(db_path=str(tmp_path / "vayu.db"))
    registry = ActionExecutorRegistry(store)

    provider = _CountingCredentialProvider()
    provider.put(
        "linkedin.owner",
        b"short-lived-linkedin-token",
        scopes=tuple(scopes),
    )
    credentials = CredentialProviderRegistry(lease_seconds=60)
    credentials.register(provider)

    organ = SocialMediaOrgan(store, credential_registry=credentials)
    adapter = _CredentialedLinkedInAdapter(fail_publish=fail_publish)
    organ.register_adapter(adapter)
    organ.bind_account(
        SocialAccountBinding(
            platform=SocialPlatform.LINKEDIN,
            account_id="owner-linkedin",
            adapter_id=adapter.adapter_id,
            credential_ref=(
                SocialCredentialReference(provider="memory", key="linkedin.owner")
                if bind_credential
                else None
            ),
        )
    )
    organ.install_executor(registry)
    return store, registry, organ, adapter, provider


def test_social_secret_is_not_resolved_before_approved_execution(tmp_path):
    store, registry, organ, adapter, provider = _credentialed_organ(tmp_path)

    action, _ = organ.propose_publish(
        platform=SocialPlatform.LINKEDIN,
        account_id="owner-linkedin",
        text="Credential resolution belongs at the execution boundary.",
        idempotency_key="credential-boundary-2026-09-05",
    )

    assert provider.resolve_calls == 0
    assert "credential" not in action["payload"]
    assert "token" not in str(action["payload"]).lower()

    with pytest.raises(PermissionError):
        registry.execute(int(action["id"]))
    assert provider.resolve_calls == 0
    assert adapter.publish_calls == 0

    store.approve(int(action["id"]))
    result = registry.execute(int(action["id"]))

    assert result["action"]["status"] == "executed"
    assert provider.resolve_calls == 1
    assert adapter.publish_calls == 1
    assert adapter.seen_lease is not None
    assert adapter.seen_lease.closed is True


def test_required_social_scope_fails_closed_before_secret_resolution(tmp_path):
    store, registry, organ, adapter, provider = _credentialed_organ(tmp_path, scopes=("profile",))
    action, _ = organ.propose_publish(
        platform=SocialPlatform.LINKEDIN,
        account_id="owner-linkedin",
        text="Do not resolve a token with the wrong scope.",
        idempotency_key="credential-scope-2026-09-05",
    )
    store.approve(int(action["id"]))

    with pytest.raises(PermissionError, match="scope"):
        registry.execute(int(action["id"]))

    assert provider.resolve_calls == 0
    assert adapter.publish_calls == 0
    assert store.get(int(action["id"]))["status"] == "execution_failed"


def test_missing_credential_reference_fails_closed_at_execution(tmp_path):
    store, registry, organ, adapter, provider = _credentialed_organ(tmp_path, bind_credential=False)
    action, _ = organ.propose_publish(
        platform=SocialPlatform.LINKEDIN,
        account_id="owner-linkedin",
        text="Credentialed adapters need an explicit external credential locator.",
        idempotency_key="missing-credential-ref-2026-09-05",
    )
    store.approve(int(action["id"]))

    with pytest.raises(PermissionError, match="credential reference"):
        registry.execute(int(action["id"]))

    assert provider.resolve_calls == 0
    assert adapter.publish_calls == 0
    assert store.get(int(action["id"]))["status"] == "execution_failed"


def test_credential_lease_closes_when_platform_publish_fails(tmp_path):
    store, registry, organ, adapter, provider = _credentialed_organ(tmp_path, fail_publish=True)
    action, _ = organ.propose_publish(
        platform=SocialPlatform.LINKEDIN,
        account_id="owner-linkedin",
        text="Lease cleanup must survive provider failures.",
        idempotency_key="credential-cleanup-2026-09-05",
    )
    store.approve(int(action["id"]))

    with pytest.raises(RuntimeError, match="simulated provider failure"):
        registry.execute(int(action["id"]))

    assert provider.resolve_calls == 1
    assert adapter.seen_lease is not None
    assert adapter.seen_lease.closed is True
    assert store.get(int(action["id"]))["status"] == "execution_failed"
