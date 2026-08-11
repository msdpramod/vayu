from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BrainResult:
    text: str
    provider: str


class Brain:
    """Provider boundary for Vayu's future LLM reasoning layer.

    The core remains runnable without an external API key. A real provider can be
    plugged in behind this interface without giving the model direct OS access.
    """

    def __init__(self) -> None:
        self.provider = os.getenv("VAYU_LLM_PROVIDER", "local")

    def respond(self, prompt: str) -> BrainResult:
        if self.provider == "local":
            return BrainResult(
                text="Vayu's local brain is online. Install an LLM provider adapter for open-ended reasoning.",
                provider="local",
            )
        return BrainResult(
            text=f"LLM provider '{self.provider}' is configured but its adapter is not installed yet.",
            provider=self.provider,
        )
