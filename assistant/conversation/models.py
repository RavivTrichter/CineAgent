"""Data models for conversation management."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConfidenceLevel(str, Enum):
    VERIFIED = "verified"
    GENERAL_KNOWLEDGE = "general"
    MIXED = "mixed"


@dataclass
class Message:
    role: MessageRole
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: ConfidenceLevel | None = None
    tool_calls: list[dict] | None = None
    tool_results: list[dict] | None = None
    thinking: str | None = None
    metadata: dict | None = None


@dataclass
class Conversation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str | None = None
    messages: list[Message] = field(default_factory=list)
    summary: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
