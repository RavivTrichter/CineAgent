# CineAssist

AI-powered film assistant for discovering movies, checking showtimes, and booking tickets at Tel Aviv cinemas. Built with Claude, FastAPI, and Streamlit.

## Architecture

Two independent services:

- **Cinema API** (`cinema_api/`) — Mock cinema REST API with SQLite (port 8000)
- **Assistant** (`assistant/`) — Agentic AI assistant with FastAPI backend (port 8001) and Streamlit chat UI (port 8501)

## External APIs

| API | Purpose | Why |
|-----|---------|-----|
| **TMDB** (The Movie Database) | Movie search, details, cast/crew, similar movies, trending, streaming platform availability | Comprehensive and well-documented, free tier with generous limits |
| **OMDB** (Open Movie Database) | Aggregated ratings (IMDb, Rotten Tomatoes, Metacritic), box office, awards | Complements TMDB with multi-source ratings that TMDB doesn't aggregate |
| **Cinema API** (internal mock) | Cinemas, showtimes, seat availability, ticket booking | No suitable free cinema API was available — real cinema chain APIs require business partnerships or geo-restricted access. We built a realistic mock with transactional booking and auto-generated showtimes relative to today's date. |

## Key Design Decisions

- **Agentic tool-use loop** — Claude autonomously decides which tools to call, executes them, reads results, and iterates (up to 10 times) before responding. Supports multi-step queries like "find a comedy playing tonight and book 2 tickets."
- **Adaptive thinking** — Claude reasons deeply on complex queries (booking flows, multi-movie comparisons) and responds quickly on simple ones.
- **Hallucination management** — Three layers: (1) system prompt rules mandating tool use for factual claims, (2) code-level heuristic flagging unverified ratings/prices/figures, (3) confidence badges (Verified / Mixed / General Knowledge) shown to the user.
- **Booking safety** — Claude must fetch fresh showtimes before every booking (never reuse stale IDs) and get explicit user confirmation.
- **LLM abstraction** — `LLMProvider` ABC makes it straightforward to add other providers (GPT, Gemini) without changing the assistant service.
- **Conversation persistence** — `ConversationStore` ABC backed by SQLite, swappable to Redis/Postgres.

## Quick Start

### 1. Setup (one-time)

```bash
./setup.sh
```

This creates a `cineagent` conda environment (Python 3.11), installs all dependencies, and creates a `.env` file for your API keys.

Edit `.env` with your keys:

| Key | Source |
|-----|--------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `TMDB_API_KEY` | [themoviedb.org](https://www.themoviedb.org/settings/api) → **Read Access Token** (the long `eyJ...` token) |
| `OMDB_API_KEY` | [omdbapi.com/apikey.aspx](http://www.omdbapi.com/apikey.aspx) |

### 2. Run

```bash
conda activate cineagent
./start.sh          # CLI chat (default)
./start.sh --ui     # Streamlit UI at http://localhost:8501
```

This starts both backend services in the background and launches the CLI or Streamlit UI in the foreground. Press `Ctrl+C` to stop everything.

Logs are saved to `logs/<timestamp>/`.

## Testing

```bash
make test
```

Runs 89 unit tests (no API keys required).

## Development

For running individual services:

```bash
make cinema      # Cinema API on :8000
make assistant   # Assistant API on :8001
make ui          # Streamlit UI on :8501
make cli         # CLI chat
```
