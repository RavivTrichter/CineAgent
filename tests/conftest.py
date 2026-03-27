"""Shared test fixtures."""

import os
import tempfile

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from cinema_api.db import init_db, seed_db


@pytest_asyncio.fixture
async def cinema_db_path():
    """Create a temporary database for cinema API tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    await init_db(db_path)
    await seed_db(db_path)
    yield db_path
    os.unlink(db_path)


@pytest_asyncio.fixture
async def cinema_client(cinema_db_path):
    """Cinema API test client with seeded database."""
    from cinema_api.db import get_db
    from cinema_api.main import app

    app.state.db = await get_db(cinema_db_path)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    await app.state.db.close()


@pytest_asyncio.fixture
async def conversation_store():
    """In-memory SQLite conversation store."""
    from assistant.conversation.sqlite_store import SQLiteConversationStore

    store = SQLiteConversationStore(":memory:")
    await store.init_db()
    return store
