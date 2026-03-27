"""Tests for the assistant service orchestrator."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from assistant.config import AssistantSettings
from assistant.conversation.models import ConfidenceLevel, MessageRole
from assistant.exceptions import TMDBError
from assistant.llm.base import LLMResponse
from assistant.services.assistant_service import AssistantService


def _make_settings():
    return MagicMock(
        spec=AssistantSettings,
        context_window_size=20,
        summary_threshold=30,
        max_tool_iterations=5,
    )


def _make_llm_response(text=None, tool_calls=None, thinking=None, stop_reason="end_turn"):
    raw_blocks = []
    if thinking:
        raw_blocks.append({"type": "thinking", "thinking": thinking, "signature": "sig"})
    if text:
        raw_blocks.append({"type": "text", "text": text})
    for tc in (tool_calls or []):
        raw_blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]})

    return LLMResponse(
        text=text,
        tool_calls=tool_calls or [],
        thinking=thinking,
        stop_reason=stop_reason,
        usage={"input_tokens": 100, "output_tokens": 50},
        raw_content_blocks=raw_blocks,
    )


class TestAssistantService:
    @pytest.mark.asyncio
    async def test_simple_text_response(self, conversation_store):
        llm = AsyncMock()
        llm.chat = AsyncMock(
            return_value=_make_llm_response(text="Hello! How can I help?", thinking="User said hi")
        )

        service = AssistantService(
            llm=llm,
            store=conversation_store,
            providers={},
            settings=_make_settings(),
        )

        conv = await conversation_store.create_conversation()
        result = await service.chat(conv.id, "Hi")

        assert result["text"] == "Hello! How can I help?"
        assert result["confidence"] == "general"
        assert result["thinking"] == "User said hi"

    @pytest.mark.asyncio
    async def test_tool_call_response(self, conversation_store):
        llm = AsyncMock()

        # First call: tool use, second call: text response
        llm.chat = AsyncMock(
            side_effect=[
                _make_llm_response(
                    tool_calls=[{"id": "t1", "name": "search_movies", "input": {"query": "Sinners"}}],
                    thinking="I should search",
                    stop_reason="tool_use",
                ),
                _make_llm_response(text="I found Sinners — a horror film.", thinking="Got results"),
            ]
        )

        tmdb = AsyncMock()
        tmdb.search_movies = AsyncMock(return_value=[{"id": 1, "title": "Sinners"}])

        service = AssistantService(
            llm=llm,
            store=conversation_store,
            providers={"tmdb": tmdb},
            settings=_make_settings(),
        )

        conv = await conversation_store.create_conversation()
        result = await service.chat(conv.id, "Find Sinners")

        assert result["text"] == "I found Sinners — a horror film."
        assert result["confidence"] == "verified"
        assert len(result["tool_calls_made"]) == 1
        tmdb.search_movies.assert_called_once_with(query="Sinners")

    @pytest.mark.asyncio
    async def test_tool_failure_graceful(self, conversation_store):
        llm = AsyncMock()
        llm.chat = AsyncMock(
            side_effect=[
                _make_llm_response(
                    tool_calls=[{"id": "t1", "name": "search_movies", "input": {"query": "X"}}],
                    stop_reason="tool_use",
                ),
                _make_llm_response(text="Sorry, I couldn't find that movie."),
            ]
        )

        tmdb = AsyncMock()
        tmdb.search_movies = AsyncMock(side_effect=TMDBError("API down"))

        service = AssistantService(
            llm=llm,
            store=conversation_store,
            providers={"tmdb": tmdb},
            settings=_make_settings(),
        )

        conv = await conversation_store.create_conversation()
        result = await service.chat(conv.id, "Find X")

        assert result["text"] == "Sorry, I couldn't find that movie."
        assert result["confidence"] == "general"

    @pytest.mark.asyncio
    async def test_confidence_verified(self, conversation_store):
        service = AssistantService(
            llm=AsyncMock(), store=conversation_store, providers={}, settings=_make_settings()
        )
        result = {
            "tool_calls_made": [{"name": "search_movies"}],
            "tool_results": [{"tool": "search_movies", "result": {"status": "success"}}],
        }
        assert service._compute_confidence(result) == ConfidenceLevel.VERIFIED

    @pytest.mark.asyncio
    async def test_confidence_general(self, conversation_store):
        service = AssistantService(
            llm=AsyncMock(), store=conversation_store, providers={}, settings=_make_settings()
        )
        result = {"tool_calls_made": [], "tool_results": []}
        assert service._compute_confidence(result) == ConfidenceLevel.GENERAL_KNOWLEDGE

    @pytest.mark.asyncio
    async def test_confidence_mixed(self, conversation_store):
        service = AssistantService(
            llm=AsyncMock(), store=conversation_store, providers={}, settings=_make_settings()
        )
        result = {
            "tool_calls_made": [{"name": "a"}, {"name": "b"}],
            "tool_results": [
                {"tool": "a", "result": {"status": "success"}},
                {"tool": "b", "result": {"status": "error", "error": "fail"}},
            ],
        }
        assert service._compute_confidence(result) == ConfidenceLevel.MIXED

    @pytest.mark.asyncio
    async def test_messages_saved(self, conversation_store):
        llm = AsyncMock()
        llm.chat = AsyncMock(return_value=_make_llm_response(text="Response"))

        service = AssistantService(
            llm=llm, store=conversation_store, providers={}, settings=_make_settings()
        )

        conv = await conversation_store.create_conversation()
        await service.chat(conv.id, "Hello")

        messages = await conversation_store.get_messages(conv.id)
        assert len(messages) == 2
        assert messages[0].role == MessageRole.USER
        assert messages[1].role == MessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_auto_title(self, conversation_store):
        llm = AsyncMock()
        llm.chat = AsyncMock(return_value=_make_llm_response(text="Hi"))

        service = AssistantService(
            llm=llm, store=conversation_store, providers={}, settings=_make_settings()
        )

        conv = await conversation_store.create_conversation()
        await service.chat(conv.id, "Tell me about Sinners")

        updated = await conversation_store.get_conversation(conv.id)
        assert updated.title == "Tell me about Sinners"
