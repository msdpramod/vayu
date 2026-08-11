from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class BrainReply:
    text: str
    provider: str


class BrainProvider(ABC):
    @abstractmethod
    def reason(self, prompt: str) -> BrainReply:
        raise NotImplementedError


class LocalFallbackProvider(BrainProvider):
    """Offline-safe provider used until an external LLM is configured."""

    def reason(self, prompt: str) -> BrainReply:
        return BrainReply(
            text=(
                "Vayu has no external AI provider configured yet. "
                "The request was routed safely but was not executed: " + prompt
            ),
            provider="local-fallback",
        )


def get_provider() -> BrainProvider:
    # External providers will be selected here using environment configuration.
    # Never commit API keys; providers must read secrets from environment variables.
    _ = os.getenv("VAYU_AI_PROVIDER", "local")
    return LocalFallbackProvider()
