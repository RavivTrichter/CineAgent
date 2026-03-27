"""Abstract base class for conversation storage."""

from abc import ABC, abstractmethod

from assistant.conversation.models import Conversation, Message


class ConversationStore(ABC):
    @abstractmethod
    async def init_db(self) -> None:
        """Initialize the storage backend."""
        ...

    @abstractmethod
    async def create_conversation(self) -> Conversation:
        """Create a new conversation and return it."""
        ...

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Conversation:
        """Get a conversation by ID, including all messages."""
        ...

    @abstractmethod
    async def list_conversations(self, limit: int = 50) -> list[Conversation]:
        """List conversations ordered by most recent, without full messages."""
        ...

    @abstractmethod
    async def add_message(self, conversation_id: str, message: Message) -> None:
        """Add a message to a conversation."""
        ...

    @abstractmethod
    async def get_messages(
        self, conversation_id: str, limit: int | None = None
    ) -> list[Message]:
        """Get messages for a conversation, optionally limited."""
        ...

    @abstractmethod
    async def update_summary(self, conversation_id: str, summary: str) -> None:
        """Update the conversation summary."""
        ...

    @abstractmethod
    async def update_title(self, conversation_id: str, title: str) -> None:
        """Update the conversation title."""
        ...

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation and its messages."""
        ...
