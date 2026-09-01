from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
from typing import Protocol

from app.actions import ActionExecutorRegistry, ProposedActionStore


SOCIAL_PUBLISH_TOOL = "social.publish"
MAX_MEDIA_REFS = 8
MAX_IDEMPOTENCY_KEY_LENGTH = 128


class SocialPlatform(str, Enum):
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    X = "x"
    YOUTUBE = "youtube"


@dataclass(frozen=True)
class SocialCapabilities:
    platform: SocialPlatform
    max_text_chars: int
    media_types: tuple[str, ...] = ()
    can_publish: bool = True

    def __post_init__(self) -> None:
        if not 1 <= self.max_text_chars <= 100_000:
            raise ValueError("max_text_chars must be between 1 and 100000")
        if len(self.media_types) > 16:
            raise ValueError("media_types is bounded to 16 entries")
        if len(set(self.media_types)) != len(self.media_types):
            raise ValueError("media_types must not contain duplicates")


@dataclass(frozen=True)
class SocialAccountBinding:
    platform: SocialPlatform
    account_id: str
    adapter_id: str

    def __post_init__(self) -> None:
        if not self.account_id.strip() or len(self.account_id) > 200:
            raise ValueError("account_id is required and bounded to 200 characters")
        if not self.adapter_id.strip() or len(self.adapter_id) > 100:
            raise ValueError("adapter_id is required and bounded to 100 characters")


@dataclass(frozen=True)
class SocialPublishRequest:
    platform: SocialPlatform
    account_id: str
    text: str
    media_refs: tuple[str, ...]
    idempotency_key: str


@dataclass(frozen=True)
class PublishReceipt:
    post_id: str
    permalink: str | None
    evidence: str
    verified: bool

    def __post_init__(self) -> None:
        if not self.post_id.strip() or len(self.post_id) > 300:
            raise ValueError("publish receipt requires a bounded post_id")
        if self.permalink is not None and len(self.permalink) > 2000:
            raise ValueError("publish receipt permalink is too long")
        if not self.evidence.strip() or len(self.evidence) > 1000:
            raise ValueError("publish receipt requires bounded verification evidence")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SocialHealth:
    connected: bool
    detail: str

    def __post_init__(self) -> None:
        if not self.detail.strip() or len(self.detail) > 500:
            raise ValueError("health detail is required and bounded")


@dataclass(frozen=True)
class SocialOrganEvent:
    kind: str
    platform: SocialPlatform
    account_id: str
    message: str
    action_id: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "platform": self.platform.value,
            "account_id": self.account_id,
            "message": self.message,
            "action_id": self.action_id,
        }


class SocialPlatformAdapter(Protocol):
    """Official-platform adapter contract. Credentials remain outside Vayu action payloads."""

    adapter_id: str
    platform: SocialPlatform

    def capabilities(self, account_id: str) -> SocialCapabilities: ...

    def health(self, account_id: str) -> SocialHealth: ...

    def publish(self, request: SocialPublishRequest) -> PublishReceipt: ...


def _bounded_text(value: str, field: str, limit: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} is required")
    if len(normalized) > limit:
        raise ValueError(f"{field} exceeds {limit} characters")
    return normalized


def _validate_idempotency_key(value: str) -> str:
    key = _bounded_text(value, "idempotency_key", MAX_IDEMPOTENCY_KEY_LENGTH)
    if len(key) < 8:
        raise ValueError("idempotency_key must be at least 8 characters")
    return key


def _validate_media_refs(media_refs: tuple[str, ...], capabilities: SocialCapabilities) -> None:
    if len(media_refs) > MAX_MEDIA_REFS:
        raise ValueError(f"media_refs is bounded to {MAX_MEDIA_REFS} items")
    for ref in media_refs:
        normalized = _bounded_text(ref, "media_ref", 500)
        if ":" not in normalized:
            raise ValueError("media_ref must use '<type>:<opaque-reference>' format")
        media_type, opaque_ref = normalized.split(":", 1)
        if not opaque_ref.strip():
            raise ValueError("media_ref requires an opaque reference")
        if media_type not in capabilities.media_types:
            raise ValueError(f"media type '{media_type}' is not supported by this adapter")


def _validated_receipt(receipt: PublishReceipt) -> PublishReceipt:
    if not receipt.verified:
        raise RuntimeError("platform publish was not verified")
    if receipt.permalink is None and not receipt.evidence.strip():
        raise RuntimeError("platform publish lacks verification evidence")
    return receipt


class SocialMediaOrgan:
    """Coordinates social adapters while delegating authority to Vayu's action gate.

    Account bindings are intentionally process-local in this first increment. Losing a
    binding on restart fails closed instead of retaining stale authority. Tokens and
    OAuth material are never accepted by this contract.
    """

    def __init__(self, action_store: ProposedActionStore):
        self.action_store = action_store
        self._adapters: dict[str, SocialPlatformAdapter] = {}
        self._bindings: dict[tuple[SocialPlatform, str], SocialAccountBinding] = {}

    def register_adapter(self, adapter: SocialPlatformAdapter) -> None:
        adapter_id = _bounded_text(adapter.adapter_id, "adapter_id", 100)
        if adapter_id in self._adapters:
            raise ValueError(f"adapter '{adapter_id}' is already registered")
        self._adapters[adapter_id] = adapter

    def bind_account(self, binding: SocialAccountBinding) -> SocialOrganEvent:
        adapter = self._adapters.get(binding.adapter_id)
        if adapter is None:
            raise LookupError(f"adapter '{binding.adapter_id}' is not registered")
        if adapter.platform != binding.platform:
            raise ValueError("account platform does not match adapter platform")
        health = adapter.health(binding.account_id)
        if not health.connected:
            raise ConnectionError(f"social platform is disconnected: {health.detail}")
        self._bindings[(binding.platform, binding.account_id)] = binding
        return SocialOrganEvent(
            kind="connected",
            platform=binding.platform,
            account_id=binding.account_id,
            message="Social account is connected and ready for approval-gated publishing.",
        )

    def status(self, platform: SocialPlatform, account_id: str) -> SocialOrganEvent:
        binding = self._bindings.get((platform, account_id))
        if binding is None:
            return SocialOrganEvent(
                kind="disconnected",
                platform=platform,
                account_id=account_id,
                message="Social account is not bound to an available Vayu adapter.",
            )
        health = self._adapters[binding.adapter_id].health(account_id)
        return SocialOrganEvent(
            kind="connected" if health.connected else "disconnected",
            platform=platform,
            account_id=account_id,
            message=(
                "Social account is connected."
                if health.connected
                else "Social platform adapter is unavailable; reconnect before publishing."
            ),
        )

    def _resolve(self, platform: SocialPlatform, account_id: str) -> tuple[SocialAccountBinding, SocialPlatformAdapter]:
        binding = self._bindings.get((platform, account_id))
        if binding is None:
            raise PermissionError("social account is not explicitly bound")
        adapter = self._adapters.get(binding.adapter_id)
        if adapter is None or adapter.platform != platform:
            raise PermissionError("bound social adapter is unavailable or mismatched")
        health = adapter.health(account_id)
        if not health.connected:
            raise ConnectionError(f"social platform is disconnected: {health.detail}")
        return binding, adapter

    def propose_publish(
        self,
        *,
        platform: SocialPlatform,
        account_id: str,
        text: str,
        idempotency_key: str,
        media_refs: tuple[str, ...] = (),
    ) -> tuple[dict[str, object], SocialOrganEvent]:
        binding, adapter = self._resolve(platform, account_id)
        capabilities = adapter.capabilities(account_id)
        if capabilities.platform != platform or not capabilities.can_publish:
            raise PermissionError("adapter does not currently permit publishing")
        normalized_text = _bounded_text(text, "text", capabilities.max_text_chars)
        normalized_key = _validate_idempotency_key(idempotency_key)
        _validate_media_refs(media_refs, capabilities)

        action = self.action_store.propose(
            tool=SOCIAL_PUBLISH_TOOL,
            description=f"Publish approved content to {platform.value} account {account_id}",
            payload={
                "platform": platform.value,
                "account_id": account_id,
                "adapter_id": binding.adapter_id,
                "text": normalized_text,
                "media_refs": list(media_refs),
                "idempotency_key": normalized_key,
            },
            risk="confirm",
        )
        event = SocialOrganEvent(
            kind="approval_required",
            platform=platform,
            account_id=account_id,
            message="Social content is ready and requires approval before publishing.",
            action_id=int(action["id"]),
        )
        return action, event

    def execute_publish_payload(self, payload: dict[str, object]) -> dict[str, object]:
        try:
            platform = SocialPlatform(str(payload["platform"]))
            account_id = str(payload["account_id"])
            adapter_id = str(payload["adapter_id"])
            text = str(payload["text"])
            media_refs_raw = payload.get("media_refs", [])
            idempotency_key = str(payload["idempotency_key"])
        except (KeyError, ValueError) as exc:
            raise ValueError("invalid social publish payload") from exc
        if not isinstance(media_refs_raw, list) or not all(isinstance(item, str) for item in media_refs_raw):
            raise ValueError("media_refs must be a list of strings")
        media_refs = tuple(media_refs_raw)

        binding, adapter = self._resolve(platform, account_id)
        if binding.adapter_id != adapter_id:
            raise PermissionError("approved adapter binding changed before execution")
        capabilities = adapter.capabilities(account_id)
        normalized_text = _bounded_text(text, "text", capabilities.max_text_chars)
        normalized_key = _validate_idempotency_key(idempotency_key)
        _validate_media_refs(media_refs, capabilities)

        receipt = adapter.publish(
            SocialPublishRequest(
                platform=platform,
                account_id=account_id,
                text=normalized_text,
                media_refs=media_refs,
                idempotency_key=normalized_key,
            )
        )
        return _validated_receipt(receipt).to_dict()

    def install_executor(self, registry: ActionExecutorRegistry) -> None:
        registry.register(SOCIAL_PUBLISH_TOOL, self.execute_publish_payload)


class MockSocialAdapter:
    """Deterministic no-network adapter for local development and CI."""

    def __init__(
        self,
        platform: SocialPlatform = SocialPlatform.LINKEDIN,
        adapter_id: str = "mock.linkedin",
        *,
        connected: bool = True,
        max_text_chars: int = 3000,
        media_types: tuple[str, ...] = ("image", "video"),
    ):
        self.platform = platform
        self.adapter_id = adapter_id
        self.connected = connected
        self._capabilities = SocialCapabilities(platform, max_text_chars, media_types)
        self._receipts: dict[str, PublishReceipt] = {}
        self.publish_calls = 0

    def capabilities(self, account_id: str) -> SocialCapabilities:
        _bounded_text(account_id, "account_id", 200)
        return self._capabilities

    def health(self, account_id: str) -> SocialHealth:
        _bounded_text(account_id, "account_id", 200)
        return SocialHealth(
            connected=self.connected,
            detail="mock adapter connected" if self.connected else "mock adapter disconnected",
        )

    def publish(self, request: SocialPublishRequest) -> PublishReceipt:
        if not self.connected:
            raise ConnectionError("mock adapter disconnected")
        cached = self._receipts.get(request.idempotency_key)
        if cached is not None:
            return cached
        self.publish_calls += 1
        digest = sha256(
            f"{request.platform.value}|{request.account_id}|{request.idempotency_key}".encode("utf-8")
        ).hexdigest()[:20]
        receipt = PublishReceipt(
            post_id=f"mock-{digest}",
            permalink=f"https://example.invalid/{request.platform.value}/posts/mock-{digest}",
            evidence="deterministic_mock_receipt",
            verified=True,
        )
        self._receipts[request.idempotency_key] = receipt
        return receipt
