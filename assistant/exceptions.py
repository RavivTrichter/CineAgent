"""Custom exceptions for the Assistant service."""


class CineAssistError(Exception):
    """Base exception for all Assistant errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# --- LLM Errors ---


class LLMError(CineAssistError):
    """Base for LLM-related errors."""
    pass


class LLMConnectionError(LLMError):
    def __init__(self, provider: str, detail: str = ""):
        super().__init__(f"Failed to connect to {provider}: {detail}", 502)


class LLMRateLimitError(LLMError):
    def __init__(self, retry_after: float | None = None):
        msg = "LLM rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after}s"
        super().__init__(msg, 429)


class LLMResponseParseError(LLMError):
    def __init__(self, detail: str):
        super().__init__(f"Failed to parse LLM response: {detail}", 500)


# --- Provider Errors ---


class ProviderError(CineAssistError):
    """Base for external API provider errors."""
    pass


class TMDBError(ProviderError):
    def __init__(self, detail: str):
        super().__init__(f"TMDB API error: {detail}", 502)


class OMDBError(ProviderError):
    def __init__(self, detail: str):
        super().__init__(f"OMDB API error: {detail}", 502)


class CinemaAPIError(ProviderError):
    def __init__(self, detail: str):
        super().__init__(f"Cinema API error: {detail}", 502)


# --- Conversation Errors ---


class ConversationError(CineAssistError):
    """Base for conversation storage errors."""
    pass


class ConversationNotFoundError(ConversationError):
    def __init__(self, conversation_id: str):
        super().__init__(f"Conversation {conversation_id} not found", 404)


class MessageSaveError(ConversationError):
    def __init__(self, detail: str):
        super().__init__(f"Failed to save message: {detail}", 500)


# --- Tool Errors ---


class ToolExecutionError(CineAssistError):
    def __init__(self, tool_name: str, detail: str):
        super().__init__(f"Tool '{tool_name}' failed: {detail}", 500)
