# CineAssist — Project Conventions

## Architecture

Two independent services:
1. `cinema_api/` — Mock cinema API (FastAPI + SQLite, port 8000)
2. `assistant/` — Film assistant (FastAPI + Streamlit + Claude, port 8001 / 8501)

## Running

```bash
make install     # Install all dependencies
make cinema      # Start Cinema API on :8000
make assistant   # Start Assistant API on :8001
make ui          # Start Streamlit UI on :8501
make test        # Run all tests
```

Run all three services (cinema, assistant, ui) in separate terminals.

## Environment Variables

Copy `.env.example` to `.env` and fill in your API keys:
```
ANTHROPIC_API_KEY=...
TMDB_API_KEY=...
OMDB_API_KEY=...
```

## Code Conventions

- Python 3.11+
- Async everywhere (aiosqlite, httpx, anthropic async client)
- Pydantic for data validation, pydantic-settings for config
- ABC base classes for all pluggable components (LLMProvider, ConversationStore, providers)
- Custom exception hierarchies — never bare `except`
- Type hints on all function signatures

## Adding a New Film to the Cinema Database

1. Open `cinema_api/db.py`
2. Add the film to the `SEED_FILMS` list:
   ```python
   ("Film Title", 2025, tmdb_id_or_None, imdb_id_or_None, "Genre1, Genre2", runtime_minutes, oscar_nominations),
   ```
3. Delete the existing `cinema.db` file (or run `make seed`)
4. Restart the Cinema API — it will re-seed automatically
5. No changes needed in the assistant — it queries the Cinema API dynamically

## Adding a New Tool

1. Add the tool schema to `assistant/llm/tools.py` in the `TOOLS` list
2. Add the mapping in `TOOL_REGISTRY`: `"tool_name": ("provider_key", "method_name")`
3. Implement the provider method in the appropriate provider class
4. Update the system prompt in `assistant/services/assistant_service.py` if needed
5. Add tests for the new provider method and tool execution

## Key Design Decisions

- Extended thinking enabled for chain-of-thought visibility
- Thinking blocks are preserved across tool-use turns (required by Claude API)
- Confidence scoring is deterministic: tools called + succeeded = VERIFIED
- Context summarization triggered at 30 messages, keeps last 20 in full
- Booking always requires explicit user confirmation (enforced in system prompt AND tool description)
- Tool errors are returned to Claude as context (not raised to user), allowing graceful recovery

## Testing

```bash
make test                          # Run all tests
python3 -m pytest tests/ -v       # Verbose output
python3 -m pytest tests/test_cinema_api/ -v  # Cinema API only
python3 -m pytest tests/test_assistant/ -v   # Assistant only
```
