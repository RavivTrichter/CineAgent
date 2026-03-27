# CineAssist

AI-powered film assistant for discovering movies, checking showtimes, and booking tickets at Tel Aviv cinemas. Built with Claude, FastAPI, and Streamlit.

## Architecture

Two independent services:

- **Cinema API** (`cinema_api/`) — Mock cinema REST API with SQLite (port 8000)
- **Assistant** (`assistant/`) — AI assistant with FastAPI backend (port 8001) and Streamlit chat UI (port 8501)

## Setup

### 1. Install dependencies

```bash
make install
```

Requires Python 3.11+.

### 2. Configure API keys

```bash
cp .env.example .env
```

Edit `.env` with your keys:

| Key | Source |
|-----|--------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `TMDB_API_KEY` | [themoviedb.org](https://www.themoviedb.org/settings/api) → **Read Access Token** (the long `eyJ...` token) |
| `OMDB_API_KEY` | [omdbapi.com/apikey.aspx](http://www.omdbapi.com/apikey.aspx) |

### 3. Seed the cinema database

The Cinema API auto-seeds on first startup with 4 Tel Aviv cinemas and 10 Oscar 2026 nominee films. To reset:

```bash
make seed       # deletes cinema.db
make cinema     # restart to re-seed
```

### 4. Run the services

Start each in a separate terminal:

```bash
make cinema      # Terminal 1 — Cinema API on :8000
make assistant   # Terminal 2 — Assistant API on :8001
make ui          # Terminal 3 — Streamlit UI on :8501
```

Open **http://localhost:8501** in your browser.

## Testing

```bash
make test
```

Runs 67 unit tests (no API keys required).
