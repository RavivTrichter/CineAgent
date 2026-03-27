"""Tests for request ID middleware."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from assistant.conversation.sqlite_store import SQLiteConversationStore


@pytest.fixture
async def middleware_client(conversation_store):
    """Client that exercises the middleware stack."""
    from unittest.mock import AsyncMock

    from assistant.main import app

    app.state.store = conversation_store
    app.state.service = AsyncMock()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


class TestRequestIDMiddleware:
    @pytest.mark.asyncio
    async def test_generates_request_id(self, middleware_client):
        resp = await middleware_client.get("/health")
        assert resp.status_code == 200
        request_id = resp.headers.get("x-request-id")
        assert request_id is not None
        # Should be a valid UUID
        uuid.UUID(request_id)

    @pytest.mark.asyncio
    async def test_echoes_provided_request_id(self, middleware_client):
        custom_id = "my-custom-request-id-123"
        resp = await middleware_client.get(
            "/health", headers={"x-request-id": custom_id}
        )
        assert resp.status_code == 200
        assert resp.headers.get("x-request-id") == custom_id

    @pytest.mark.asyncio
    async def test_unique_ids_per_request(self, middleware_client):
        resp1 = await middleware_client.get("/health")
        resp2 = await middleware_client.get("/health")
        id1 = resp1.headers.get("x-request-id")
        id2 = resp2.headers.get("x-request-id")
        assert id1 != id2
