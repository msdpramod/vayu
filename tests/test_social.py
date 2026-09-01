from app.actions import ActionExecutorRegistry, ProposedActionStore
from app.social import CallableSocialAdapter, SocialMediaOrgan, SocialPublishRequest


def build_organ(tmp_path):
    store = ProposedActionStore(str(tmp_path / "vayu.db"), approval_ttl_seconds=60)
    registry = ActionExecutorRegistry(store)
    return store, registry, SocialMediaOrgan(store, registry)


def test_preview_requires_approval_and_reports_configuration(tmp_path):
    _, _, organ = build_organ(tmp_path)

    preview = organ.preview(SocialPublishRequest("linkedin", "Hello world"))

    assert preview["platform"] == "linkedin"
    assert preview["requires_approval"] is True
    assert preview["configured"] is False


def test_social_publish_is_never_executed_before_explicit_approval(tmp_path):
    store, registry, organ = build_organ(tmp_path)
    calls = []
    organ.register_adapter(
        CallableSocialAdapter(
            "linkedin",
            lambda payload: calls.append(payload) or {"post_id": "post-123"},
        )
    )

    action = organ.propose(SocialPublishRequest("linkedin", "Approved content"))

    assert action["status"] == "pending_approval"
    assert action["risk"] == "confirm"
    try:
        registry.execute(action["id"])
        assert False, "execution should have required approval"
    except PermissionError:
        pass
    assert calls == []

    store.approve(action["id"])
    result = registry.execute(action["id"])

    assert result["action"]["status"] == "executed"
    assert result["result"]["post_id"] == "post-123"
    assert calls[0]["text"] == "Approved content"


def test_platform_mismatch_is_rejected(tmp_path):
    store, registry, organ = build_organ(tmp_path)
    organ.register_adapter(
        CallableSocialAdapter("linkedin", lambda payload: {"post_id": "post-123"})
    )

    action = store.propose(
        "social.publish.linkedin",
        "tampered",
        {"platform": "x", "text": "bad", "media_urls": [], "metadata": {}},
        "confirm",
    )
    store.approve(action["id"])

    try:
        registry.execute(action["id"])
        assert False, "mismatched platform must fail"
    except ValueError:
        pass

    assert store.get(action["id"])["status"] == "execution_failed"


def test_adapter_must_return_verifiable_result(tmp_path):
    store, registry, organ = build_organ(tmp_path)
    organ.register_adapter(CallableSocialAdapter("x", lambda payload: {"ok": True}))
    action = organ.propose(SocialPublishRequest("x", "hello"))
    store.approve(action["id"])

    try:
        registry.execute(action["id"])
        assert False, "unverifiable publish result must fail"
    except RuntimeError:
        pass

    assert store.get(action["id"])["status"] == "execution_failed"
