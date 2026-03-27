# CineAssist — Technical Architecture

## System Overview

CineAssist is a two-service system: a mock cinema REST API and an AI-powered assistant that uses tool calling to answer movie questions and book tickets.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
│                  Streamlit (port 8501)                          │
│              streamlit_app.py                                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────────────────┐
│                    Assistant API (port 8001)                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              AssistantService (orchestrator)              │   │
│  │  - Agentic loop (up to 5 tool iterations)               │   │
│  │  - Confidence scoring                                    │   │
│  │  - Context window management + summarization             │   │
│  └────┬──────────┬──────────┬──────────────────────────────┘   │
│       │          │          │                                    │
│  ┌────▼───┐ ┌───▼────┐ ┌──▼─────┐                             │
│  │ Claude │ │  TMDB  │ │  OMDB  │    LLM + External Providers  │
│  │Gemini  │ │Provider│ │Provider│                               │
│  └────────┘ └────────┘ └────────┘                               │
│       │                                                         │
│  ┌────▼─────────────────┐                                      │
│  │  ConversationStore   │  SQLite persistence                   │
│  │  (SQLite)            │                                       │
│  └──────────────────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
                       │ HTTP (tools call this)
┌──────────────────────▼──────────────────────────────────────────┐
│                    Cinema API (port 8000)                        │
│                                                                 │
│  /cinemas          → list/get cinemas                           │
│  /films            → list/search/get films                      │
│  /showtimes        → list with filters (film, cinema, date)     │
│  /bookings         → create booking, get by reference           │
│                                                                 │
│  SQLite database, auto-seeded on startup                        │
└─────────────────────────────────────────────────────────────────┘
```

## Service 1: Cinema API (`cinema_api/`)

A standalone FastAPI service simulating a real cinema chain's API.

### Key Files

| File | Purpose |
|------|---------|
| `main.py` | App entry point, lifespan (DB init + seed), exception handlers |
| `db.py` | SQLite schema, seed data (4 cinemas, 10 films), showtime generation |
| `models.py` | Pydantic models: `Cinema`, `Film`, `Showtime`, `BookingRequest`, `BookingResponse` |
| `exceptions.py` | `CinemaServiceError` hierarchy (not found, insufficient seats, etc.) |
| `config.py` | `CinemaSettings` via pydantic-settings |
| `routers/` | REST endpoints for cinemas, films, showtimes, bookings |

### Seed Data

- **4 cinemas** in the Tel Aviv metro area
- **10 films** (2026 Oscar nominees) with genres, runtime, nomination counts
- **Showtimes** auto-generated for today + 6 days, randomized across cinemas with realistic pricing (35-55 ILS)

### Booking Flow

```
POST /bookings { showtime_id, num_tickets, customer_name, customer_email }
  1. Validate showtime exists
  2. Check available_seats >= num_tickets (inside transaction)
  3. Decrement available_seats
  4. Generate booking reference (CINE-XXXXXXXX)
  5. Return BookingResponse with reference, total price, confirmation
```

The booking is **transactional** — seat count and booking insert happen atomically. In a production system, this would use a proper database with row-level locking and a payment gateway integration.

## Service 2: Assistant (`assistant/`)

The AI assistant orchestrates an LLM with tool calling to serve as a movie concierge.

### Class Hierarchy

```
LLMProvider (ABC)
├── ClaudeProvider     — Anthropic Claude with extended thinking
└── GeminiProvider     — Google Gemini with thinking support

ConversationStore (ABC)
└── SQLiteConversationStore — Persistent conversation + message storage

BaseProvider
├── TMDBProvider       — Movie search, details, similar, trending
├── OMDBProvider       — Ratings (IMDb/RT/Metacritic), awards, box office
└── CinemaProvider     — Cinemas, showtimes, booking (calls Cinema API)

AssistantService       — Core orchestrator (agentic loop, confidence, context)
```

### Exception Hierarchy

```
CineAssistError (base, carries status_code)
├── LLMError
│   ├── LLMConnectionError (502)
│   ├── LLMRateLimitError (429)
│   └── LLMResponseParseError (500)
├── ProviderError
│   ├── TMDBError (502)
│   ├── OMDBError (502)
│   └── CinemaAPIError (502)
├── ConversationError
│   ├── ConversationNotFoundError (404)
│   └── MessageSaveError (500)
└── ToolExecutionError (500)
```

Tool errors are caught and **returned to the LLM as context** (not raised to the user), allowing the assistant to recover gracefully or explain the failure.

### The Agentic Loop

This is the core of the assistant. When a user sends a message:

```
User message
    │
    ▼
┌─ AssistantService.chat() ──────────────────────────────────────┐
│  1. Save user message to ConversationStore                      │
│  2. Auto-title conversation from first message                  │
│  3. Build context (summary + sliding window of 20 messages)     │
│  4. Enter agentic loop:                                         │
│     ┌──────────────────────────────────────────────────────┐   │
│     │  Call LLM with messages + system prompt + 8 tools     │   │
│     │       │                                               │   │
│     │  stop_reason == "tool_use"?                           │   │
│     │    YES → Execute each tool call                       │   │
│     │         → Append results to messages                  │   │
│     │         → Loop again (max 5 iterations)               │   │
│     │    NO  → Return final text response                   │   │
│     └──────────────────────────────────────────────────────┘   │
│  5. Compute confidence (VERIFIED / MIXED / GENERAL_KNOWLEDGE)   │
│  6. Save assistant message                                      │
│  7. Maybe trigger context summarization (>30 messages)          │
└─────────────────────────────────────────────────────────────────┘
```

### Available Tools (8)

| Tool | Provider | Purpose |
|------|----------|---------|
| `search_movies` | TMDB | Search by title/keywords |
| `get_movie_details` | TMDB | Full details (cast, crew, genres, runtime) |
| `get_similar_movies` | TMDB | "Movies like X" recommendations |
| `get_trending_movies` | TMDB | Currently trending films |
| `get_movie_ratings` | OMDB | Ratings from IMDb, RT, Metacritic + awards |
| `get_nearby_cinemas` | Cinema API | List cinemas, optionally filtered by city |
| `get_showtimes` | Cinema API | Showtimes with film/cinema/date filters |
| `book_tickets` | Cinema API | Book tickets (requires user confirmation) |

Tools are defined in `llm/tools.py` with a `TOOL_REGISTRY` that maps each tool name to a `(provider_key, method_name)` tuple. Adding a new tool requires:
1. Add schema to `TOOLS` list
2. Add mapping to `TOOL_REGISTRY`
3. Implement the method on the provider

### Confidence Scoring

Deterministic, based on tool usage:

| Level | Condition | UI Badge |
|-------|-----------|----------|
| `VERIFIED` | All tools called and succeeded | Green |
| `MIXED` | Some tools succeeded, some failed | Blue |
| `GENERAL_KNOWLEDGE` | No tools called (or all failed) | Yellow |

### Context Management

- **Sliding window**: Last 20 messages are sent in full to the LLM
- **Summarization**: When conversation exceeds 30 messages, older messages are summarized by the LLM into a paragraph that's prepended to context
- **Thinking preservation**: Claude's thinking block signatures are preserved across tool-use turns (required by the API)

### LLM Provider Switching

Set `LLM_PROVIDER` in `.env`:

```
LLM_PROVIDER=claude    # default
LLM_PROVIDER=gemini    # alternative
```

Both providers implement the same `LLMProvider` ABC. The factory in `main.py` instantiates the correct one. `AssistantService` is provider-agnostic — it only depends on the abstract interface.

### Conversation Persistence

Conversations and messages are stored in SQLite (`assistant.db`):

- **conversations** table: id, title, summary, created_at, updated_at
- **messages** table: id, conversation_id, role, content, confidence, thinking, tool_calls (JSON), tool_results (JSON), metadata (JSON), timestamp

The `ConversationStore` ABC allows swapping to PostgreSQL/Redis/etc. without changing `AssistantService`.

## Production Considerations

This is a demo/assignment project. In a real-world deployment:

| Area | Current | Production |
|------|---------|------------|
| **Database** | SQLite (file-based) | PostgreSQL with connection pooling |
| **Booking** | Optimistic seat decrement | Row-level locking + payment gateway |
| **Auth** | None | JWT/OAuth2 with user accounts |
| **Cinema data** | Seeded mock data | Real cinema chain API integration |
| **Caching** | None | Redis for TMDB/OMDB responses |
| **Rate limiting** | None | Per-user rate limits on LLM calls |
| **Deployment** | Local `make` commands | Docker Compose / Kubernetes |
| **Monitoring** | Console logs | Structured logging + APM (Datadog/etc.) |
