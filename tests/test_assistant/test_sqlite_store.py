"""Tests for SQLite conversation store."""

import pytest

from assistant.conversation.models import ConfidenceLevel, Message, MessageRole
from assistant.exceptions import ConversationNotFoundError


class TestConversationStore:
    @pytest.mark.asyncio
    async def test_create_conversation(self, conversation_store):
        conv = await conversation_store.create_conversation()
        assert conv.id is not None
        assert conv.title is None

    @pytest.mark.asyncio
    async def test_get_conversation(self, conversation_store):
        conv = await conversation_store.create_conversation()
        fetched = await conversation_store.get_conversation(conv.id)
        assert fetched.id == conv.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, conversation_store):
        with pytest.raises(ConversationNotFoundError):
            await conversation_store.get_conversation("nonexistent")

    @pytest.mark.asyncio
    async def test_add_and_get_messages(self, conversation_store):
        conv = await conversation_store.create_conversation()
        msg = Message(role=MessageRole.USER, content="Hello")
        await conversation_store.add_message(conv.id, msg)

        messages = await conversation_store.get_messages(conv.id)
        assert len(messages) == 1
        assert messages[0].content == "Hello"
        assert messages[0].role == MessageRole.USER

    @pytest.mark.asyncio
    async def test_message_with_metadata(self, conversation_store):
        conv = await conversation_store.create_conversation()
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="Response",
            confidence=ConfidenceLevel.VERIFIED,
            tool_calls=[{"name": "search_movies"}],
            tool_results=[{"tool": "search_movies", "result": {"status": "success"}}],
            thinking="I should search for movies.",
        )
        await conversation_store.add_message(conv.id, msg)

        messages = await conversation_store.get_messages(conv.id)
        assert messages[0].confidence == ConfidenceLevel.VERIFIED
        assert messages[0].tool_calls == [{"name": "search_movies"}]
        assert messages[0].thinking == "I should search for movies."

    @pytest.mark.asyncio
    async def test_list_conversations(self, conversation_store):
        await conversation_store.create_conversation()
        await conversation_store.create_conversation()
        convs = await conversation_store.list_conversations()
        assert len(convs) == 2

    @pytest.mark.asyncio
    async def test_update_title(self, conversation_store):
        conv = await conversation_store.create_conversation()
        await conversation_store.update_title(conv.id, "Movie Chat")
        fetched = await conversation_store.get_conversation(conv.id)
        assert fetched.title == "Movie Chat"

    @pytest.mark.asyncio
    async def test_update_summary(self, conversation_store):
        conv = await conversation_store.create_conversation()
        await conversation_store.update_summary(conv.id, "We discussed Sinners.")
        fetched = await conversation_store.get_conversation(conv.id)
        assert fetched.summary == "We discussed Sinners."

    @pytest.mark.asyncio
    async def test_delete_conversation(self, conversation_store):
        conv = await conversation_store.create_conversation()
        msg = Message(role=MessageRole.USER, content="Hi")
        await conversation_store.add_message(conv.id, msg)

        await conversation_store.delete_conversation(conv.id)
        with pytest.raises(ConversationNotFoundError):
            await conversation_store.get_conversation(conv.id)
