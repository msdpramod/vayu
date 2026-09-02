from __future__ import annotations

import sqlite3

import pytest

from app.actions import ActionExecutorRegistry, ProposedActionStore
from app.social import MockSocialAdapter, SocialAccountBinding, SocialMediaOrgan, SocialPlatform
from app.social_identity import SocialCredentialReference


def _setup(db_path: str):
    actions = ProposedActionStore(db_path=db_path)
    registry = ActionExecutorRegistry(actions)
    organ = SocialMediaOrgan(actions)
    adapter = MockSocialAdapter()
    organ.register_adapter(adapter)
    organ.install_executor(registry)
    return actions, registry, organ, adapter


def test_social_binding_survives_process_reconstruction_without_persisting_secrets(tmp_path):
    db_path = str(tmp_path / "vayu.db")
    _, _, organ, adapter = _setup(db_path)
    credential_ref = SocialCredentialReference(provider="keychain", key="social/linkedin/owner")
    organ.bind_account(
        SocialAccountBinding(
            platform=SocialPlatform.LINKEDIN,
            account_id="owner-linkedin",
            adapter_id=adapter.adapter_id,
            credential_ref=credential_ref,
        )
    )

    # Reconstruct the organ as a new process would. Durable identity survives, but
    # the adapter must still be installed explicitly before the account is usable.
    actions2 = ProposedActionStore(db_path=db_path)
    organ2 = SocialMediaOrgan(actions2)
    assert organ2.status(SocialPlatform.LINKEDIN, "owner-linkedin").kind == "disconnected"
    organ2.register_adapter(MockSocialAdapter())
    assert organ2.status(SocialPlatform.LINKEDIN, "owner-linkedin").kind == "connected"

    with sqlite3.connect(db_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(social_account_bindings)").fetchall()
        }
    assert "access_token" not in columns
    assert "refresh_token" not in columns
    assert "password" not in columns
    assert "cookie" not in columns


def test_credential_reference_rejects_secret_like_uri_or_serialized_material():
    with pytest.raises(ValueError):
        SocialCredentialReference(provider="keychain", key="https://vault.example/token?id=abc")
    with pytest.raises(ValueError):
        SocialCredentialReference(provider="env", key="Bearer secret-token")


def test_credential_reference_never_enters_publish_action_payload(tmp_path):
    db_path = str(tmp_path / "vayu.db")
    actions, _, organ, adapter = _setup(db_path)
    organ.bind_account(
        SocialAccountBinding(
            platform=SocialPlatform.LINKEDIN,
            account_id="owner-linkedin",
            adapter_id=adapter.adapter_id,
            credential_ref=SocialCredentialReference(provider="keychain", key="social/linkedin/owner"),
        )
    )

    action, _ = organ.propose_publish(
        platform=SocialPlatform.LINKEDIN,
        account_id="owner-linkedin",
        text="Credential references stay outside action payloads.",
        idempotency_key="durable-binding-payload-001",
    )

    payload = actions.get(int(action["id"]))["payload"]
    assert payload["binding_revision"] == 1
    assert "credential_ref" not in payload
    assert "credential_provider" not in payload
    assert "credential_key" not in payload


def test_revocation_after_approval_prevents_publish(tmp_path):
    db_path = str(tmp_path / "vayu.db")
    actions, registry, organ, adapter = _setup(db_path)
    organ.bind_account(
        SocialAccountBinding(
            platform=SocialPlatform.LINKEDIN,
            account_id="owner-linkedin",
            adapter_id=adapter.adapter_id,
        )
    )
    action, _ = organ.propose_publish(
        platform=SocialPlatform.LINKEDIN,
        account_id="owner-linkedin",
        text="This must not publish after account revocation.",
        idempotency_key="revocation-after-approval-001",
    )
    actions.approve(int(action["id"]))
    organ.revoke_account(SocialPlatform.LINKEDIN, "owner-linkedin")

    with pytest.raises(PermissionError, match="not explicitly bound"):
        registry.execute(int(action["id"]))
    assert adapter.publish_calls == 0
    assert actions.get(int(action["id"]))["status"] == "execution_failed"


def test_rebinding_increments_revision_and_invalidates_old_approval(tmp_path):
    db_path = str(tmp_path / "vayu.db")
    actions, registry, organ, adapter = _setup(db_path)
    organ.bind_account(
        SocialAccountBinding(
            platform=SocialPlatform.LINKEDIN,
            account_id="owner-linkedin",
            adapter_id=adapter.adapter_id,
            credential_ref=SocialCredentialReference(provider="keychain", key="social/linkedin/owner-v1"),
        )
    )
    action, _ = organ.propose_publish(
        platform=SocialPlatform.LINKEDIN,
        account_id="owner-linkedin",
        text="An approval is bound to the identity revision it reviewed.",
        idempotency_key="identity-revision-approval-001",
    )
    actions.approve(int(action["id"]))

    organ.revoke_account(SocialPlatform.LINKEDIN, "owner-linkedin")
    organ.bind_account(
        SocialAccountBinding(
            platform=SocialPlatform.LINKEDIN,
            account_id="owner-linkedin",
            adapter_id=adapter.adapter_id,
            credential_ref=SocialCredentialReference(provider="keychain", key="social/linkedin/owner-v2"),
        )
    )

    with pytest.raises(PermissionError, match="identity changed"):
        registry.execute(int(action["id"]))
    assert adapter.publish_calls == 0
    assert actions.get(int(action["id"]))["status"] == "execution_failed"


def test_active_binding_cannot_be_silently_repointed(tmp_path):
    db_path = str(tmp_path / "vayu.db")
    _, _, organ, adapter = _setup(db_path)
    organ.bind_account(
        SocialAccountBinding(
            platform=SocialPlatform.LINKEDIN,
            account_id="owner-linkedin",
            adapter_id=adapter.adapter_id,
            credential_ref=SocialCredentialReference(provider="keychain", key="social/linkedin/owner-v1"),
        )
    )

    with pytest.raises(PermissionError, match="revoke"):
        organ.bind_account(
            SocialAccountBinding(
                platform=SocialPlatform.LINKEDIN,
                account_id="owner-linkedin",
                adapter_id=adapter.adapter_id,
                credential_ref=SocialCredentialReference(provider="keychain", key="social/linkedin/owner-v2"),
            )
        )
