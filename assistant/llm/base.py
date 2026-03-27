"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    text: str | None
    tool_calls: list[dict] = field(default_factory=list)
    thinking: str | None = None
    stop_reason: str = "end_turn"
    usage: dict = field(default_factory=dict)
    raw_content_blocks: list = field(default_factory=list)


class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Send messages to LLM, optionally with tool definitions."""
        ...
