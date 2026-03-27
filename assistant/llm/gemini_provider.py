"""Google Gemini LLM provider with thinking and tool use."""

import logging
import uuid

from google import genai
from google.genai import types

from assistant.config import AssistantSettings
from assistant.exceptions import (
    LLMConnectionError,
    LLMRateLimitError,
)
from assistant.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self, settings: AssistantSettings):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        self.max_tokens = settings.max_tokens
        self.thinking_budget = settings.thinking_budget_tokens

    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        try:
            contents = self._build_contents(messages)
            config = self._build_config(system_prompt, tools)

            logger.info(
                "Calling Gemini: model=%s, messages=%d, tools=%s",
                self.model,
                len(messages),
                len(tools) if tools else 0,
            )

            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            logger.info(
                "Gemini response: finish_reason=%s, usage=%s",
                response.candidates[0].finish_reason if response.candidates else "none",
                response.usage_metadata,
            )

            return self._parse_response(response)

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str:
                logger.warning("Gemini rate limit hit: %s", e)
                raise LLMRateLimitError() from e
            logger.error("Gemini API error: %s", e)
            raise LLMConnectionError("Gemini", str(e)) from e

    def _build_contents(self, messages: list[dict]) -> list[types.Content]:
        """Convert our message format to Gemini Content objects."""
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            content = msg["content"]

            if isinstance(content, str):
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))
            elif isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "tool_result":
                            parts.append(types.Part.from_function_response(
                                name=block.get("name", "tool"),
                                response={"result": block.get("content", "")},
                            ))
                        elif block.get("type") == "text":
                            parts.append(types.Part.from_text(text=block.get("text", "")))
                        elif block.get("type") == "tool_use":
                            parts.append(types.Part(function_call=types.FunctionCall(
                                name=block["name"],
                                args=block.get("input", {}),
                            )))
                    else:
                        parts.append(types.Part.from_text(text=str(block)))
                if parts:
                    contents.append(types.Content(role=role, parts=parts))

        return contents

    def _build_config(
        self, system_prompt: str, tools: list[dict] | None
    ) -> types.GenerateContentConfig:
        """Build Gemini config from system prompt and tool definitions."""
        config_kwargs = {
            "system_instruction": system_prompt,
            "max_output_tokens": self.max_tokens,
            "thinking_config": types.ThinkingConfig(
                thinking_budget=self.thinking_budget,
            ),
        }

        if tools:
            gemini_tools = self._convert_tools(tools)
            config_kwargs["tools"] = gemini_tools

        return types.GenerateContentConfig(**config_kwargs)

    def _convert_tools(self, tools: list[dict]) -> list[types.Tool]:
        """Convert our tool format to Gemini FunctionDeclarations."""
        declarations = []
        for tool in tools:
            declarations.append(
                types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters_json_schema=tool["input_schema"],
                )
            )
        return [types.Tool(function_declarations=declarations)]

    def _parse_response(self, response) -> LLMResponse:
        """Parse Gemini response into our LLMResponse format."""
        text = None
        tool_calls = []
        thinking = None

        if not response.candidates:
            return LLMResponse(text="No response generated.", stop_reason="error")

        candidate = response.candidates[0]
        parts = candidate.content.parts if candidate.content else []

        thinking_parts = []
        for part in parts:
            if hasattr(part, "thought") and part.thought:
                thinking_parts.append(part.text)
            elif hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                tool_calls.append({
                    "id": getattr(fc, "id", None) or f"call_{uuid.uuid4().hex[:12]}",
                    "name": fc.name,
                    "input": dict(fc.args) if fc.args else {},
                })
            elif hasattr(part, "text") and part.text:
                text = part.text

        if thinking_parts:
            thinking = "\n\n".join(thinking_parts)

        # Determine stop reason
        finish_reason = str(candidate.finish_reason) if candidate.finish_reason else "STOP"
        if tool_calls:
            stop_reason = "tool_use"
        elif "STOP" in finish_reason:
            stop_reason = "end_turn"
        elif "MAX_TOKENS" in finish_reason:
            stop_reason = "max_tokens"
        else:
            stop_reason = "end_turn"

        # Build usage
        usage = {}
        if response.usage_metadata:
            um = response.usage_metadata
            usage = {
                "input_tokens": getattr(um, "prompt_token_count", 0) or 0,
                "output_tokens": getattr(um, "candidates_token_count", 0) or 0,
            }

        # Build raw content blocks for multi-turn replay
        raw_blocks = []
        for part in parts:
            if hasattr(part, "thought") and part.thought:
                raw_blocks.append({"type": "thinking", "text": part.text})
            elif hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                raw_blocks.append({
                    "type": "tool_use",
                    "id": getattr(fc, "id", None) or f"call_{uuid.uuid4().hex[:12]}",
                    "name": fc.name,
                    "input": dict(fc.args) if fc.args else {},
                })
            elif hasattr(part, "text") and part.text:
                raw_blocks.append({"type": "text", "text": part.text})

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            thinking=thinking,
            stop_reason=stop_reason,
            usage=usage,
            raw_content_blocks=raw_blocks,
        )
