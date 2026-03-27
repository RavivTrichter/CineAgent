"""Tests for assistant FastAPI endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from assistant.conversation.models import Conversation, Message, MessageRole
from assistant.conversation.sqlite_store import SQLiteConversationStore


@pytest.fixture
def mock_service():
    service = AsyncMock()
    service.chat = AsyncMock(
        return_value={
            "text": "Test response",
            "confidence": "general",
            "thinking": None,
            "tool_calls_made": [],
        }
    )
    return service


@pytest.fixture
async def api_client(conversation_store, mock_service):
    from assistant.main import app

    app.state.service = mock_service
    app.state.store = conversation_store

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


class TestConversationEndpoints:
    @pytest.mark.asyncio
    async def test_create_conversation(self, api_client):
        resp = await api_client.post("/conversations")
        assert resp.status_code == 200
        assert "id" in resp.json()

    @pytest.mark.asyncio
    async def test_list_conversations(self, api_client):
        await api_client.post("/conversations")
        await api_client.post("/conversations")

        resp = await api_client.get("/conversations")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_get_conversation(self, api_client):
        create_resp = await api_client.post("/conversations")
        conv_id = create_resp.json()["id"]

        resp = await api_client.get(f"/conversations/{conv_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == conv_id

    @pytest.mark.asyncio
    async def test_delete_conversation(self, api_client):
        create_resp = await api_client.post("/conversations")
        conv_id = create_resp.json()["id"]

        resp = await api_client.delete(f"/conversations/{conv_id}")
        assert resp.status_code == 200

        resp = await api_client.get(f"/conversations/{conv_id}")
        assert resp.status_code == 404


class TestChatEndpoint:
    @pytest.mark.asyncio
    async def test_send_message(self, api_client, mock_service):
        create_resp = await api_client.post("/conversations")
        conv_id = create_resp.json()["id"]

        resp = await api_client.post(
            f"/conversations/{conv_id}/messages",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "Test response"
        assert data["confidence"] == "general"

    @pytest.mark.asyncio
    async def test_send_message_nonexistent_conversation(self, api_client, mock_service):
        from assistant.exceptions import ConversationNotFoundError

        mock_service.chat = AsyncMock(
            side_effect=ConversationNotFoundError("nonexistent")
        )

        resp = await api_client.post(
            "/conversations/nonexistent/messages",
            json={"message": "Hello"},
        )
        assert resp.status_code == 404


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health(self, api_client):
        resp = await api_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
