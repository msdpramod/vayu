from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Callable

from app.actions import ProposedActionStore, ActionExecutorRegistry, actions, executors


SUPPORTED_PLATFORMS = {"linkedin", "instagram", "facebook", "x", "youtube"}


@dataclass(frozen=True)
class SocialPublishRequest:
    platform: str
    text: str
    media_urls: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

    def normalized(self) -> "SocialPublishRequest":
        platform = self.platform.strip().lower()
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported social platform: {platform}")
        text = self.text.strip()
        if not text and not self.media_urls:
            raise ValueError("A social post requires text or at least one media URL.")
        if len(text) > 20_000:
            raise ValueError("Social post text exceeds Vayu's maximum payload length.")
        return SocialPublishRequest(
            platform=platform,
            text=text,
            media_urls=tuple(url.strip() for url in self.media_urls if url.strip()),
            metadata=dict(self.metadata or {}),
        )


class SocialAdapter:
    """Platform adapter contract. Implementations must return a verifiable publish result."""

    platform: str

    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    def publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class DisabledPlatformAdapter(SocialAdapter):
    """Safe default until OAuth credentials and a real adapter are configured."""

    def __init__(self, platform: str):
        self.platform = platform

    def health(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "configured": False,
            "status": "credentials_required",
        }

    def publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(
            f"{self.platform} publishing is not configured. "
            "Connect an approved OAuth application before enabling this adapter."
        )


class CallableSocialAdapter(SocialAdapter):
    """Small production boundary for SDK/API-backed platform implementations."""

    def __init__(
        self,
        platform: str,
        publisher: Callable[[dict[str, Any]], dict[str, Any]],
        healthcheck: Callable[[], dict[str, Any]] | None = None,
    ):
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported social platform: {platform}")
        self.platform = platform
        self._publisher = publisher
        self._healthcheck = healthcheck

    def health(self) -> dict[str, Any]:
        if self._healthcheck is None:
            return {"platform": self.platform, "configured": True, "status": "ready"}
        result = dict(self._healthcheck())
        result.setdefault("platform", self.platform)
        return result

    def publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self._publisher(payload)
        if not isinstance(result, dict):
            raise RuntimeError("Social adapter returned an invalid result.")
        if not result.get("post_id") and not result.get("url"):
            raise RuntimeError("Social adapter did not return a verifiable post_id or URL.")
        return result


class SocialMediaOrgan:
    """Vayu organ for social publishing with mandatory action approval."""

    TOOL_PREFIX = "social.publish."

    def __init__(
        self,
        store: ProposedActionStore,
        registry: ActionExecutorRegistry,
    ):
        self.store = store
        self.registry = registry
        self._adapters: dict[str, SocialAdapter] = {}
        for platform in sorted(SUPPORTED_PLATFORMS):
            self.register_adapter(DisabledPlatformAdapter(platform))

    def register_adapter(self, adapter: SocialAdapter) -> None:
        if adapter.platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported social platform: {adapter.platform}")
        self._adapters[adapter.platform] = adapter
        self.registry.register(
            f"{self.TOOL_PREFIX}{adapter.platform}",
            lambda payload, platform=adapter.platform: self._publish_now(platform, payload),
        )

    def platforms(self) -> list[dict[str, Any]]:
        return [self._adapters[name].health() for name in sorted(self._adapters)]

    def preview(self, request: SocialPublishRequest) -> dict[str, Any]:
        item = request.normalized()
        return {
            "platform": item.platform,
            "text": item.text,
            "media_urls": list(item.media_urls),
            "metadata": item.metadata or {},
            "requires_approval": True,
            "configured": bool(self._adapters[item.platform].health().get("configured")),
        }

    def propose(self, request: SocialPublishRequest) -> dict[str, Any]:
        item = request.normalized()
        payload = {
            "platform": item.platform,
            "text": item.text,
            "media_urls": list(item.media_urls),
            "metadata": item.metadata or {},
        }
        return self.store.propose(
            tool=f"{self.TOOL_PREFIX}{item.platform}",
            description=f"Publish approved content to {item.platform}",
            payload=payload,
            risk="confirm",
        )

    def _publish_now(self, platform: str, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("platform") != platform:
            raise ValueError("Social action platform does not match its executor.")
        adapter = self._adapters.get(platform)
        if adapter is None:
            raise RuntimeError(f"No adapter is installed for {platform}.")
        return adapter.publish(payload)


def _configure_from_environment(organ: SocialMediaOrgan) -> None:
    """Reserved provider hook.

    OAuth secrets are intentionally not interpreted by the core yet. Platform-specific
    adapters should be registered by deployment code/SDK integrations rather than
    embedding tokens or unofficial browser automation in Vayu.
    """
    _ = os.getenv("VAYU_SOCIAL_ADAPTERS", "")


social = SocialMediaOrgan(actions, executors)
_configure_from_environment(social)
