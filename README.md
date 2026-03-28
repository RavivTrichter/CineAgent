# CineAssist

AI-powered film assistant for discovering movies, checking showtimes, and booking tickets at Tel Aviv cinemas. Built with Claude, FastAPI, and Streamlit.

## Architecture

Two independent services:

- **Cinema API** (`cinema_api/`) — Mock cinema REST API with SQLite (port 8000)
- **Assistant** (`assistant/`) — AI assistant with FastAPI backend (port 8001) and Streamlit chat UI (port 8501)

## Quick Start

### 1. Setup

```bash
./setup.sh
```

Creates a `cineagent` conda environment (Python 3.11), installs all dependencies, and prompts you to configure API keys in `.env`.

| Key | Source |
|-----|--------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `TMDB_API_KEY` | [themoviedb.org](https://www.themoviedb.org/settings/api) → **Read Access Token** (the long `eyJ...` token) |
| `OMDB_API_KEY` | [omdbapi.com/apikey.aspx](http://www.omdbapi.com/apikey.aspx) |

### 2. Run

```bash
conda activate cineagent
./start.sh          # CLI chat (default)
./start.sh --ui     # Streamlit UI on :8501
```

This starts Cinema API (:8000) and Assistant API (:8001) in the background, then launches the CLI or UI in the foreground. Logs are saved to `logs/<timestamp>/`.

Press `Ctrl+C` to stop everything, or run `./stop.sh` to kill background services.

### 3. Seed the cinema database

The Cinema API auto-seeds on first startup with 4 Tel Aviv cinemas and 10 Oscar 2026 nominee films. To reset:

```bash
make seed       # deletes cinema.db; restart to re-seed
```

## Development

For running individual services during development:

```bash
make cinema      # Cinema API on :8000
make assistant   # Assistant API on :8001
make ui          # Streamlit UI on :8501
make cli         # CLI chat
```

## Testing

```bash
make test
```

Runs 95 unit tests (no API keys required).
