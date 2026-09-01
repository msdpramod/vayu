from __future__ import annotations

import pytest

from app.actions import ActionExecutorRegistry, ProposedActionStore
from app.social import (
    MockSocialAdapter,
    PublishReceipt,
    SocialAccountBinding,
    SocialMediaOrgan,
    SocialPlatform,
)


def _organ(tmp_path):
    store = ProposedActionStore(db_path=str(tmp_path / "vayu.db"))
    registry = ActionExecutorRegistry(store)
    organ = SocialMediaOrgan(store)
    adapter = MockSocialAdapter()
    organ.register_adapter(adapter)
    organ.bind_account(
        SocialAccountBinding(
            platform=SocialPlatform.LINKEDIN,
            account_id="owner-linkedin",
            adapter_id=adapter.adapter_id,
        )
    )
    organ.install_executor(registry)
    return store, registry, organ, adapter


def test_social_publish_is_approval_gated(tmp_path):
    store, registry, organ, adapter = _organ(tmp_path)
    action, event = organ.propose_publish(
        platform=SocialPlatform.LINKEDIN,
        account_id="owner-linkedin",
        text="A production-safe Vayu update.",
        idempotency_key="post-2026-09-02-001",
    )

    assert action["tool"] == "social.publish"
    assert action["risk"] == "confirm"
    assert action["status"] == "pending_approval"
    assert event.kind == "approval_required"
    assert event.action_id == action["id"]

    with pytest.raises(PermissionError):
        registry.execute(int(action["id"]))
    assert adapter.publish_calls == 0

    store.approve(int(action["id"]))
    result = registry.execute(int(action["id"]))

    assert result["action"]["status"] == "executed"
    assert result["result"]["verified"] is True
    assert result["result"]["post_id"].startswith("mock-")
    assert adapter.publish_calls == 1


def test_duplicate_idempotency_key_returns_same_platform_receipt(tmp_path):
    store, registry, organ, adapter = _organ(tmp_path)

    receipts = []
    for _ in range(2):
        action, _ = organ.propose_publish(
            platform=SocialPlatform.LINKEDIN,
            account_id="owner-linkedin",
            text="Same intended platform operation.",
            idempotency_key="stable-request-2026-09-02",
        )
        store.approve(int(action["id"]))
        receipts.append(registry.execute(int(action["id"]))["result"])

    assert receipts[0]["post_id"] == receipts[1]["post_id"]
    assert adapter.publish_calls == 1


def test_disconnected_platform_fails_closed_before_proposal(tmp_path):
    store = ProposedActionStore(db_path=str(tmp_path / "vayu.db"))
    organ = SocialMediaOrgan(store)
    adapter = MockSocialAdapter(connected=False)
    organ.register_adapter(adapter)

    with pytest.raises(ConnectionError):
        organ.bind_account(
            SocialAccountBinding(
                platform=SocialPlatform.LINKEDIN,
                account_id="owner-linkedin",
                adapter_id=adapter.adapter_id,
            )
        )

    assert store.list() == []
    status = organ.status(SocialPlatform.LINKEDIN, "owner-linkedin")
    assert status.kind == "disconnected"


def test_platform_capabilities_reject_unsupported_media_and_oversized_text(tmp_path):
    _, _, organ, _ = _organ(tmp_path)

    with pytest.raises(ValueError, match="not supported"):
        organ.propose_publish(
            platform=SocialPlatform.LINKEDIN,
            account_id="owner-linkedin",
            text="post",
            media_refs=("audio:asset-1",),
            idempotency_key="unsupported-media-1",
        )

    with pytest.raises(ValueError, match="exceeds"):
        organ.propose_publish(
            platform=SocialPlatform.LINKEDIN,
            account_id="owner-linkedin",
            text="x" * 3001,
            idempotency_key="oversized-text-1",
        )


class _UnverifiedAdapter(MockSocialAdapter):
    def publish(self, request):
        self.publish_calls += 1
        return PublishReceipt(
            post_id="provider-returned-id",
            permalink=None,
            evidence="provider response lacked verification",
            verified=False,
        )


def test_unverified_publish_receipt_becomes_terminal_execution_failure(tmp_path):
    store = ProposedActionStore(db_path=str(tmp_path / "vayu.db"))
    registry = ActionExecutorRegistry(store)
    organ = SocialMediaOrgan(store)
    adapter = _UnverifiedAdapter()
    organ.register_adapter(adapter)
    organ.bind_account(
        SocialAccountBinding(
            platform=SocialPlatform.LINKEDIN,
            account_id="owner-linkedin",
            adapter_id=adapter.adapter_id,
        )
    )
    organ.install_executor(registry)

    action, _ = organ.propose_publish(
        platform=SocialPlatform.LINKEDIN,
        account_id="owner-linkedin",
        text="Do not claim success without evidence.",
        idempotency_key="verify-receipt-2026-09-02",
    )
    store.approve(int(action["id"]))

    with pytest.raises(RuntimeError, match="not verified"):
        registry.execute(int(action["id"]))

    assert store.get(int(action["id"]))["status"] == "execution_failed"


def test_binding_is_platform_specific(tmp_path):
    store = ProposedActionStore(db_path=str(tmp_path / "vayu.db"))
    organ = SocialMediaOrgan(store)
    adapter = MockSocialAdapter()
    organ.register_adapter(adapter)

    with pytest.raises(ValueError, match="platform"):
        organ.bind_account(
            SocialAccountBinding(
                platform=SocialPlatform.INSTAGRAM,
                account_id="owner-instagram",
                adapter_id=adapter.adapter_id,
            )
        )
