# CineAssist — Progress Log (2026-03-26)

## What Was Built

The entire CineAssist project was implemented from scratch in a single session. Two independent services plus a full test suite.

## Architecture

```
cine-agent/
├── cinema_api/          # Service 1: Mock Cinema API (FastAPI + SQLite, port 8000)
├── assistant/           # Service 2: Film Assistant (FastAPI + Streamlit + Claude, port 8001/8501)
└── tests/               # 67 tests, all passing
```

## Completed Components

### Service 1: Cinema API (`cinema_api/`)
- **models.py** — Pydantic models: Cinema, Film, Showtime, ShowtimeDetail, BookingRequest, BookingResponse
- **exceptions.py** — Exception hierarchy: CinemaServiceError, ShowtimeNotFoundError, CinemaNotFoundError, FilmNotFoundError, InsufficientSeatsError, InvalidBookingError, DatabaseError
- **config.py** — CinemaSettings via pydantic-settings
- **db.py** — SQLite setup + seed data with 4 Tel Aviv cinemas and 10 Oscar 2026 nominees. Showtimes generated relative to current date (today + 0-6 days)
- **routers/cinemas.py** — GET /cinemas, GET /cinemas/{id}
- **routers/films.py** — GET /films, GET /films?search=, GET /films/{id}
- **routers/showtimes.py** — GET /showtimes (with film_id/cinema_id/date filters), GET /showtimes/{id}
- **routers/bookings.py** — POST /bookings (transactional), GET /bookings/{ref}
- **main.py** — FastAPI app with lifespan (init + seed DB on startup), exception handlers

### Service 2: Assistant (`assistant/`)
- **exceptions.py** — Full hierarchy: CineAssistError → LLMError (Connection/RateLimit/ParseError), ProviderError (TMDB/OMDB/CinemaAPI), ConversationError (NotFound/SaveError), ToolExecutionError
- **config.py** — AssistantSettings: API keys, model config, context window (20), summary threshold (30), max tool iterations (5)
- **conversation/models.py** — Message, Conversation dataclasses, MessageRole and ConfidenceLevel enums
- **conversation/base.py** — ConversationStore ABC
- **conversation/sqlite_store.py** — SQLite implementation with persistent connection (needed for :memory: test support)
- **llm/base.py** — LLMProvider ABC, LLMResponse dataclass (includes raw_content_blocks for thinking signature preservation)
- **llm/claude_provider.py** — Claude implementation with extended thinking + tool use. Maps Anthropic exceptions to custom exceptions
- **llm/tools.py** — 8 tool schemas + TOOL_REGISTRY mapping tool names to (provider, method)
- **providers/base.py** — BaseProvider with shared httpx.AsyncClient management
- **providers/tmdb.py** — search_movies, get_movie_details, get_similar_movies, get_trending_movies
- **providers/omdb.py** — get_movie_ratings (normalizes IMDb/RT/Metacritic + box office + awards)
- **providers/cinema.py** — get_cinemas, get_showtimes (resolves film title → film_id), book_tickets, get_booking
- **services/assistant_service.py** — The core orchestrator:
  - Agentic loop (tool use → execute → feed results back → repeat, max 5 iterations)
  - Confidence scoring (VERIFIED / MIXED / GENERAL_KNOWLEDGE)
  - Context management (sliding window of 20 messages + LLM-generated summary of older messages)
  - Conversation auto-titling from first message
  - System prompt enforcing hallucination prevention rules
- **main.py** — FastAPI app with CRUD endpoints for conversations + POST chat endpoint
- **streamlit_app.py** — Chat UI with:
  - Confidence badges (green verified / yellow general / blue mixed)
  - Expandable debug panel (thinking block + tool calls)
  - Conversation sidebar (new + resume past conversations)
  - Booking success cards

### Tests (`tests/`)
- **67 tests, all passing** as of end of session
- Cinema API: cinemas (5), films (5), showtimes (5), bookings (6)
- Assistant: SQLite store (9), Claude provider (6), TMDB provider (5), OMDB provider (4), Cinema provider (5), assistant service (8), API routes (7)
- Shared fixtures in conftest.py: temp DB for cinema, in-memory SQLite for conversations, mock LLM

### Project Files
- **CLAUDE.md** — Project conventions, how to run, how to add films/tools
- **Makefile** — `make install`, `make cinema`, `make ui`, `make test`, `make seed`
- **.env.example** — Template for API keys
- **.gitignore** — Standard Python ignores + .env + .db files

## Seed Data

**Cinemas:** Yes Planet Rishon LeZion, Cinema City Glilot, Lev Dizengoff, Hot Cinema Ramat Aviv

**Films (2026 Oscar nominees):**
1. Sinners (16 nominations)
2. One Battle After Another (13 nominations)
3. Frankenstein (9 nominations)
4. Sentimental Value (9 nominations)
5. Marty Supreme (9 nominations)
6. Hamnet (8 nominations)
7. Bugonia
8. F1
9. The Secret Agent
10. Train Dreams

Note: TMDB IDs and IMDB IDs are currently `None` in the seed data. These should be looked up and added for TMDB/OMDB cross-referencing to work properly.

## Known Issues / TODO for Testing

1. **API keys needed**: You need valid keys for ANTHROPIC_API_KEY, TMDB_API_KEY, and OMDB_API_KEY in `.env`
3. **TMDB/OMDB IDs missing**: Seed films don't have real tmdb_id/imdb_id values yet. The assistant will still work (it searches TMDB by title), but having IDs would improve OMDB lookups
4. **End-to-end testing not done**: Unit tests all pass, but the full flow (Streamlit → FastAPI → Claude → tools) hasn't been tested with real API keys yet
5. **Pydantic deprecation warning**: `cinema_api/config.py` uses class-based `Config` instead of `ConfigDict` — cosmetic, not breaking

## How to Start Testing

```bash
# 1. Install dependencies
make install

# 2. Set up environment
cp .env.example .env
# Edit .env with your real API keys

# 3. Run tests (no API keys needed)
make test

# 4. Start services (3 terminals)
make cinema      # Terminal 1: Cinema API on :8000
make assistant   # Terminal 2: Assistant API on :8001
make ui          # Terminal 3: Streamlit UI on :8501

# 5. Open http://localhost:8501 in browser
```

## Phase 2 (Not Yet Implemented)
- Cross-reference TMDB and OMDB data for consistency checking
- RAG layer with ChromaDB for semantic movie discovery
- Look up and add real TMDB/OMDB IDs to seed data
