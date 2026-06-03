"""TokenExtractor – Strategy Pattern für Sub-Agenten-Token-Extraktion (SPEC-0035 FR-03)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class TokenRecord:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


class TokenExtractor(ABC):
    @abstractmethod
    def extract(self, usage: Any) -> TokenRecord:
        """Extracts token counts from a provider-specific usage object."""


class ClaudeSDKTokenExtractor(TokenExtractor):
    """Extracts tokens from the Claude Agent SDK usage object."""

    def extract(self, usage: Any) -> TokenRecord:
        if usage is None:
            return TokenRecord(input_tokens=0, output_tokens=0)
        # Claude Agent SDK usage object: .input_tokens, .output_tokens, .cache_read_input_tokens
        return TokenRecord(
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )
