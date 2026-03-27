"""Tests for Gemini LLM provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from assistant.exceptions import LLMConnectionError, LLMRateLimitError
from assistant.llm.gemini_provider import GeminiProvider


def _make_settings(**kwargs):
    defaults = {
        "gemini_api_key": "test-key",
        "gemini_model": "gemini-2.5-flash",
        "max_tokens": 1024,
        "thinking_budget_tokens": 2000,
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_part(text=None, thought=False, function_call=None):
    part = MagicMock()
    part.thought = thought
    part.text = text
    part.function_call = function_call
    return part


def _make_response(parts, finish_reason="STOP"):
    response = MagicMock()
    candidate = MagicMock()
    candidate.content.parts = parts
    candidate.finish_reason = finish_reason
    response.candidates = [candidate]
    response.usage_metadata = MagicMock(
        prompt_token_count=100, candidates_token_count=50
    )
    return response


def _make_function_call(name, args, call_id=None):
    fc = MagicMock()
    fc.name = name
    fc.args = args
    fc.id = call_id
    return fc


class TestGeminiProvider:
    @pytest.mark.asyncio
    async def test_parse_text_response(self):
        provider = GeminiProvider(_make_settings())
        mock_response = _make_response([_make_part(text="Hello!")])

        with patch.object(
            provider.client.aio.models,
            "generate_content",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await provider.chat(
                messages=[{"role": "user", "content": "Hi"}],
                system_prompt="You are helpful.",
            )

        assert result.text == "Hello!"
        assert result.tool_calls == []
        assert result.stop_reason == "end_turn"

    @pytest.mark.asyncio
    async def test_parse_thinking_and_text(self):
        provider = GeminiProvider(_make_settings())
        mock_response = _make_response([
            _make_part(text="Let me think...", thought=True),
            _make_part(text="Here's the answer."),
        ])

        with patch.object(
            provider.client.aio.models,
            "generate_content",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await provider.chat(
                messages=[{"role": "user", "content": "Think"}],
                system_prompt="You are helpful.",
            )

        assert result.thinking == "Let me think..."
        assert result.text == "Here's the answer."

    @pytest.mark.asyncio
    async def test_parse_tool_use_response(self):
        provider = GeminiProvider(_make_settings())
        fc = _make_function_call("search_movies", {"query": "Sinners"}, "call_123")
        mock_response = _make_response(
            [_make_part(function_call=fc)],
            finish_reason="STOP",
        )

        with patch.object(
            provider.client.aio.models,
            "generate_content",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await provider.chat(
                messages=[{"role": "user", "content": "Find Sinners"}],
                system_prompt="You are helpful.",
                tools=[{"name": "search_movies", "description": "Search", "input_schema": {}}],
            )

        assert result.stop_reason == "tool_use"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "search_movies"
        assert result.tool_calls[0]["input"] == {"query": "Sinners"}
        assert result.tool_calls[0]["id"] == "call_123"

    @pytest.mark.asyncio
    async def test_raw_content_blocks_preserved(self):
        provider = GeminiProvider(_make_settings())
        fc = _make_function_call("search_movies", {"query": "x"}, "call_abc")
        mock_response = _make_response([
            _make_part(text="thinking here", thought=True),
            _make_part(function_call=fc),
        ])

        with patch.object(
            provider.client.aio.models,
            "generate_content",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await provider.chat(
                messages=[{"role": "user", "content": "search"}],
                system_prompt="test",
                tools=[],
            )

        assert len(result.raw_content_blocks) == 2
        assert result.raw_content_blocks[0]["type"] == "thinking"
        assert result.raw_content_blocks[1]["type"] == "tool_use"

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        provider = GeminiProvider(_make_settings())

        with patch.object(
            provider.client.aio.models,
            "generate_content",
            new_callable=AsyncMock,
            side_effect=Exception("429 rate limit exceeded"),
        ):
            with pytest.raises(LLMRateLimitError):
                await provider.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    system_prompt="test",
                )

    @pytest.mark.asyncio
    async def test_connection_error(self):
        provider = GeminiProvider(_make_settings())

        with patch.object(
            provider.client.aio.models,
            "generate_content",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            with pytest.raises(LLMConnectionError):
                await provider.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    system_prompt="test",
                )
