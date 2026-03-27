"""SQLite implementation of ConversationStore."""

import json
import logging
from datetime import datetime, timezone

import aiosqlite

from assistant.conversation.base import ConversationStore
from assistant.conversation.models import (
    ConfidenceLevel,
    Conversation,
    Message,
    MessageRole,
)
from assistant.exceptions import ConversationNotFoundError, MessageSaveError

logger = logging.getLogger(__name__)

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence TEXT,
    tool_calls TEXT,
    tool_results TEXT,
    thinking TEXT,
    metadata TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
"""


class SQLiteConversationStore(ConversationStore):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row
            await self._db.execute("PRAGMA foreign_keys = ON")
        return self._db

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def init_db(self) -> None:
        db = await self._get_db()
        await db.executescript(CREATE_TABLES)
        await db.commit()
        logger.info("Conversation store initialized.")

    async def create_conversation(self) -> Conversation:
        conv = Conversation()
        db = await self._get_db()
        await db.execute(
            "INSERT INTO conversations (id, title, summary, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conv.id, conv.title, conv.summary, conv.created_at.isoformat(), conv.updated_at.isoformat()),
        )
        await db.commit()
        return conv

    async def get_conversation(self, conversation_id: str) -> Conversation:
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise ConversationNotFoundError(conversation_id)

        messages = await self.get_messages(conversation_id)
        return Conversation(
            id=row["id"],
            title=row["title"],
            summary=row["summary"],
            messages=messages,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    async def list_conversations(self, limit: int = 50) -> list[Conversation]:
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            Conversation(
                id=row["id"],
                title=row["title"],
                summary=row["summary"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    async def add_message(self, conversation_id: str, message: Message) -> None:
        try:
            db = await self._get_db()
            await db.execute(
                """INSERT INTO messages
                   (id, conversation_id, role, content, confidence, tool_calls, tool_results, thinking, metadata, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    message.id,
                    conversation_id,
                    message.role.value,
                    message.content,
                    message.confidence.value if message.confidence else None,
                    json.dumps(message.tool_calls) if message.tool_calls else None,
                    json.dumps(message.tool_results) if message.tool_results else None,
                    message.thinking,
                    json.dumps(message.metadata) if message.metadata else None,
                    message.timestamp.isoformat(),
                ),
            )
            await db.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), conversation_id),
            )
            await db.commit()
        except Exception as e:
            raise MessageSaveError(str(e)) from e

    async def get_messages(
        self, conversation_id: str, limit: int | None = None
    ) -> list[Message]:
        db = await self._get_db()
        query = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp"
        params: list = [conversation_id]
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_message(row) for row in rows]

    async def update_summary(self, conversation_id: str, summary: str) -> None:
        db = await self._get_db()
        await db.execute(
            "UPDATE conversations SET summary = ? WHERE id = ?",
            (summary, conversation_id),
        )
        await db.commit()

    async def update_title(self, conversation_id: str, title: str) -> None:
        db = await self._get_db()
        await db.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, conversation_id),
        )
        await db.commit()

    async def delete_conversation(self, conversation_id: str) -> None:
        db = await self._get_db()
        await db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        await db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        await db.commit()

    @staticmethod
    def _row_to_message(row) -> Message:
        return Message(
            id=row["id"],
            role=MessageRole(row["role"]),
            content=row["content"],
            confidence=ConfidenceLevel(row["confidence"]) if row["confidence"] else None,
            tool_calls=json.loads(row["tool_calls"]) if row["tool_calls"] else None,
            tool_results=json.loads(row["tool_results"]) if row["tool_results"] else None,
            thinking=row["thinking"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )
