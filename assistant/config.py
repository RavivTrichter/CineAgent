"""Configuration for the Assistant service."""

from pydantic_settings import BaseSettings


class AssistantSettings(BaseSettings):
    # LLM provider selection: "claude" or "gemini"
    llm_provider: str = "claude"

    # Claude
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Shared LLM settings
    max_tokens: int = 16000
    thinking_budget_tokens: int = 5000

    # External APIs
    tmdb_api_key: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    omdb_api_key: str = ""
    omdb_base_url: str = "http://www.omdbapi.com"
    cinema_api_base_url: str = "http://localhost:8000"

    # Conversation
    context_window_size: int = 20
    summary_threshold: int = 30
    max_tool_iterations: int = 5

    # Database
    database_path: str = "assistant.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8001

    # Logging
    log_format: str = "console"
    log_level: str = "INFO"
    log_file: str | None = None

    class Config:
        env_file = ".env"
