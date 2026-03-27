"""Claude LLM provider with extended thinking and tool use."""

import anthropic
import structlog

from assistant.config import AssistantSettings
from assistant.exceptions import (
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseParseError,
)
from assistant.llm.base import LLMProvider, LLMResponse

logger = structlog.get_logger(__name__)


class ClaudeProvider(LLMProvider):
    def __init__(self, settings: AssistantSettings):
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            max_retries=5,
        )
        self.model = settings.claude_model
        self.max_tokens = settings.max_tokens
        self.thinking_budget = settings.thinking_budget_tokens

    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        try:
            kwargs: dict = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": system_prompt,
                "messages": messages,
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget,
                },
            }
            if tools:
                kwargs["tools"] = tools

            logger.info(
                "Calling Claude: model=%s, messages=%d, tools=%s",
                self.model,
                len(messages),
                len(tools) if tools else 0,
            )

            response = await self.client.messages.create(**kwargs)

            logger.info(
                "Claude response: stop_reason=%s, usage=%s",
                response.stop_reason,
                response.usage,
            )

            return self._parse_response(response)

        except anthropic.RateLimitError as e:
            logger.warning("Claude rate limit hit: %s", e)
            raise LLMRateLimitError() from e
        except anthropic.APIConnectionError as e:
            logger.error("Claude connection error: %s", e)
            raise LLMConnectionError("Claude", str(e)) from e
        except anthropic.APIStatusError as e:
            logger.error("Claude API error: status=%d, message=%s", e.status_code, e.message)
            raise LLMConnectionError("Claude", f"Status {e.status_code}: {e.message}") from e

    def _parse_response(self, response) -> LLMResponse:
        text = None
        tool_calls = []
        thinking = None

        for block in response.content:
            if block.type == "thinking":
                thinking = block.thinking
            elif block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        # Serialize raw content blocks for replay in multi-turn tool use
        raw_blocks = []
        for block in response.content:
            if block.type == "thinking":
                raw_blocks.append(
                    {
                        "type": "thinking",
                        "thinking": block.thinking,
                        "signature": block.signature,
                    }
                )
            elif block.type == "text":
                raw_blocks.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                raw_blocks.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            thinking=thinking,
            stop_reason=response.stop_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            raw_content_blocks=raw_blocks,
        )
