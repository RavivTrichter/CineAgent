"""Tests for Claude LLM provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from assistant.exceptions import LLMConnectionError, LLMRateLimitError
from assistant.llm.claude_provider import ClaudeProvider


def _make_settings(**kwargs):
    defaults = {
        "anthropic_api_key": "test-key",
        "claude_model": "claude-sonnet-4-20250514",
        "max_tokens": 1024,
        "thinking_budget_tokens": 2000,
        "tmdb_api_key": "",
        "omdb_api_key": "",
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_response(content_blocks, stop_reason="end_turn"):
    response = MagicMock()
    response.content = content_blocks
    response.stop_reason = stop_reason
    response.usage = MagicMock(input_tokens=100, output_tokens=50)
    return response


def _text_block(text):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _thinking_block(thinking, signature="sig123"):
    block = MagicMock()
    block.type = "thinking"
    block.thinking = thinking
    block.signature = signature
    return block


def _tool_use_block(tool_id, name, tool_input):
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = tool_input
    return block


class TestClaudeProvider:
    @pytest.mark.asyncio
    async def test_parse_text_response(self):
        provider = ClaudeProvider(_make_settings())
        mock_response = _make_response([_text_block("Hello!")])

        with patch.object(provider.client.messages, "create", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.chat(
                messages=[{"role": "user", "content": "Hi"}],
                system_prompt="You are helpful.",
            )

        assert result.text == "Hello!"
        assert result.tool_calls == []
        assert result.stop_reason == "end_turn"

    @pytest.mark.asyncio
    async def test_parse_thinking_and_text(self):
        provider = ClaudeProvider(_make_settings())
        mock_response = _make_response([
            _thinking_block("Let me think about this..."),
            _text_block("Here's my answer."),
        ])

        with patch.object(provider.client.messages, "create", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.chat(
                messages=[{"role": "user", "content": "Think"}],
                system_prompt="You are helpful.",
            )

        assert result.thinking == "Let me think about this..."
        assert result.text == "Here's my answer."

    @pytest.mark.asyncio
    async def test_parse_tool_use_response(self):
        provider = ClaudeProvider(_make_settings())
        mock_response = _make_response(
            [
                _thinking_block("I need to search"),
                _tool_use_block("tool_1", "search_movies", {"query": "Sinners"}),
            ],
            stop_reason="tool_use",
        )

        with patch.object(provider.client.messages, "create", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.chat(
                messages=[{"role": "user", "content": "Find Sinners"}],
                system_prompt="You are helpful.",
                tools=[{"name": "search_movies"}],
            )

        assert result.stop_reason == "tool_use"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "search_movies"
        assert result.tool_calls[0]["input"] == {"query": "Sinners"}

    @pytest.mark.asyncio
    async def test_raw_content_blocks_preserved(self):
        provider = ClaudeProvider(_make_settings())
        mock_response = _make_response([
            _thinking_block("thinking", "sig_abc"),
            _tool_use_block("t1", "search_movies", {"query": "x"}),
        ], stop_reason="tool_use")

        with patch.object(provider.client.messages, "create", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.chat(
                messages=[{"role": "user", "content": "search"}],
                system_prompt="test",
                tools=[],
            )

        assert len(result.raw_content_blocks) == 2
        assert result.raw_content_blocks[0]["type"] == "thinking"
        assert result.raw_content_blocks[0]["signature"] == "sig_abc"
        assert result.raw_content_blocks[1]["type"] == "tool_use"

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        import anthropic

        provider = ClaudeProvider(_make_settings())
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}

        with patch.object(
            provider.client.messages,
            "create",
            new_callable=AsyncMock,
            side_effect=anthropic.RateLimitError(
                message="rate limited",
                response=mock_response,
                body=None,
            ),
        ):
            with pytest.raises(LLMRateLimitError):
                await provider.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    system_prompt="test",
                )

    @pytest.mark.asyncio
    async def test_connection_error(self):
        import anthropic

        provider = ClaudeProvider(_make_settings())

        with patch.object(
            provider.client.messages,
            "create",
            new_callable=AsyncMock,
            side_effect=anthropic.APIConnectionError(request=MagicMock()),
        ):
            with pytest.raises(LLMConnectionError):
                await provider.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    system_prompt="test",
                )
