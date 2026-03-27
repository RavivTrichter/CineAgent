# CineAssist — Progress Log

## Current Status (2026-03-27)

**All core functionality is implemented, tested, and verified end-to-end.** Code is on `main` in GitHub (RavivTrichter/CineAgent).

- 67 unit tests passing
- End-to-end flow verified: Streamlit → Assistant API → Claude (with tools) → Cinema API
- All three API keys configured and working (Anthropic, TMDB, OMDB)
- Config fix applied: `max_tokens` raised to 16000 (must exceed `thinking_budget_tokens` of 5000)

## Git Workflow

- **Remote:** git@github.com:RavivTrichter/CineAgent.git (SSH)
- **No direct commits to `main`** — all changes go through feature branches + PRs
- Feature branches should be descriptive (e.g., `feature/add-tmdb-ids`, `fix/pydantic-deprecation`)

## Architecture

```
cine-agent/
├── cinema_api/          # Service 1: Mock Cinema API (FastAPI + SQLite, port 8000)
├── assistant/           # Service 2: Film Assistant (FastAPI + Streamlit + Claude, port 8001/8501)
└── tests/               # 67 tests, all passing
```

## Running Services

Each service runs in its own terminal:

```bash
make cinema      # Terminal 1: Cinema API on :8000
make assistant   # Terminal 2: Assistant API on :8001
make ui          # Terminal 3: Streamlit UI on :8501
```

## What's Done

### Service 1: Cinema API (`cinema_api/`)
- Pydantic models, exception hierarchy, config
- SQLite + seed data: 4 Tel Aviv cinemas, 10 Oscar 2026 nominees
- REST endpoints: cinemas, films (with search), showtimes (with filters), bookings (transactional)
- Showtimes auto-generated relative to current date (today + 0-6 days)

### Service 2: Assistant (`assistant/`)
- Claude integration with extended thinking + 8 tools
- Agentic loop (tool use → execute → feed back, max 5 iterations)
- Confidence scoring (VERIFIED / MIXED / GENERAL_KNOWLEDGE)
- Context management (sliding window of 20 messages + LLM summary)
- Conversation persistence (SQLite), auto-titling
- Streamlit chat UI with confidence badges, debug panel, conversation sidebar
- Providers: TMDB (search, details, similar, trending), OMDB (ratings, awards, box office), Cinema API (cinemas, showtimes, bookings)

### Tests (`tests/`)
- 67 tests: Cinema API (21) + Assistant (46)
- Shared fixtures in conftest.py, mock LLM for unit tests

## Known Issues

1. **TMDB/OMDB IDs missing** — Seed films have `None` for tmdb_id/imdb_id. Assistant works via title search, but adding IDs would improve OMDB lookups
2. **Pydantic deprecation warning** — `cinema_api/config.py` uses class-based `Config` instead of `ConfigDict` (cosmetic)

## Phase 2 — Feature Backlog

Each of these should be a separate feature branch + PR:

- [ ] Add real TMDB/OMDB IDs to seed data
- [ ] Fix Pydantic deprecation warning
- [ ] Cross-reference TMDB and OMDB data for consistency checking
- [ ] RAG layer with ChromaDB for semantic movie discovery
- [ ] Hide Streamlit "Deploy" button in UI config
