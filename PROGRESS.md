# CineAssist — Progress Log

## Current Status (2026-03-27)

**All core functionality is implemented, tested, and verified end-to-end.** Code is on `main` in GitHub (RavivTrichter/CineAgent).

- 95+ unit tests passing (67 original + 22 CLI/logging + 6 Gemini)
- End-to-end flow verified with both Claude and Gemini providers
- All API keys configured and working (Anthropic, TMDB, OMDB, Gemini)
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
- **Dual LLM support**: Claude (primary) and Gemini (alternative), switchable via `LLM_PROVIDER` env var
- Agentic loop (tool use → execute → feed back, max 5 iterations)
- Confidence scoring (VERIFIED / MIXED / GENERAL_KNOWLEDGE)
- **Hallucination detection**: heuristic flags unverified ratings, prices, and box office figures
- Context management (sliding window of 20 messages + LLM summary)
- Conversation persistence (SQLite), auto-titling
- **CLI** (Rich + Click): `chat`, `list`, `delete`, `health` commands with debug mode
- **Streamlit UI**: confidence badges, debug panel, conversation sidebar
- **Structured logging** (structlog): JSON/console output, request ID correlation
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
- [ ] Add user identity (username in sidebar, filter conversations per user)
- [ ] UI/flow tests (Streamlit AppTest, E2E test scenarios)

---

## Session 2 — 2026-03-27 (CLI + Logging + Setup Scripts)

### What was added

**PR #5 — CLI interface + structured JSON logging** (`worktree-cli-and-logging`)
- Interactive CLI chat client (`assistant/cli.py`) using Rich + Click
  - Commands: `chat` (with `--debug`), `list`, `delete`, `health`
  - Confidence badges, thinking panels, tool call tables in debug mode
- Structured logging (`assistant/logging_config.py`) via structlog
  - JSON or console output (`LOG_FORMAT` env var)
  - Configurable level (`LOG_LEVEL`) and file output (`LOG_FILE`)
- Request ID middleware (`assistant/middleware.py`) — `X-Request-ID` header for log correlation
- All modules migrated from stdlib `logging` to `structlog`
- 22 new tests (95 total, all passing)
- New deps: `structlog>=24.1.0`, `rich>=13.7.0`, `click>=8.1.0`

**PR #6 — Setup and launcher scripts** (`feature/setup-scripts`)
- `setup.sh` — creates conda env `cineagent` (Python 3.11), installs all deps
- `start.sh` — launches Cinema API + Assistant API in background, CLI/UI in foreground
- `stop.sh` — kills all services on ports 8000/8001/8501

**PR #7 — Fix setup scripts** (`fix/setup-scripts-pythonpath`)
- Fixed `ModuleNotFoundError` by setting `PYTHONPATH` to repo root
- Changed to single-terminal UX: services in background with logs to `logs/`, CLI in foreground
- Ctrl+C cleanup trap to stop everything

**PR #8 — Fix .env loading** (`fix/setup-scripts-v2`) — pending merge
- `start.sh` now sources `.env` before launching services
- Fixes `Could not resolve authentication method` error caused by pydantic-settings resolving `env_file=".env"` relative to cwd

### Quick Start (after setup)
```bash
./setup.sh                 # one-time
conda activate cineagent
./start.sh                 # services in background, CLI in foreground
./start.sh --ui            # Streamlit instead of CLI
./stop.sh                  # kill background services
```

### Known Issues (new)
3. **Claude API overload (529)** — Intermittent; Anthropic API returns 529 when overloaded. Retry after a moment.

### Terminal A PRs (same session)

**PR #2 — Google Gemini LLM provider** (`feature/gemini-provider`)
- `GeminiProvider` implements `LLMProvider` ABC with thinking + tool use
- Switchable via `LLM_PROVIDER=gemini` env var
- Factory function in `main.py` selects provider at startup
- Live e2e tested: Gemini calls tools, returns verified responses
- Note: Gemini is more cautious than Claude (asks for clarification more often, may use wrong dates)
- 6 new unit tests (mocked)

**PR #3 — Technical architecture documentation** (`docs/technical-readme`)
- `ARCHITECTURE.md` — system diagram, class hierarchy, exception tree
- Agentic loop flow, tool registry, confidence scoring explained
- Booking flow walkthrough, context management strategy
- Production vs. current comparison table

**PR #4 — Prompts, guardrails, and assignment mapping** (`feature/prompts-guardrails`)
- System prompt overhaul: chain-of-thought reasoning (5-step process), decision logic for tools vs. LLM knowledge, data fusion guidance, stronger hallucination rules, scope boundaries
- Hallucination detection: `_detect_hallucination_risk()` heuristic flags unverified ratings, prices, and box office figures in responses
- `hallucination_flags` field added to API response
- `ASSIGNMENT.md` — maps every assignment requirement to specific code and design decisions

### Worktrees

Active worktrees used during development:
```
cine-agent/              → main
cine-agent-gemini/       → feature/gemini-provider
cine-agent-docs/         → docs/technical-readme
cine-agent-prompts/      → feature/prompts-guardrails
cine-agent-cli/          → feature/cli-and-structured-logging
```

To clean up after merging:
```bash
git worktree remove /Users/ravivtrichter/repos/private/cine-agent-gemini
git worktree remove /Users/ravivtrichter/repos/private/cine-agent-docs
git worktree remove /Users/ravivtrichter/repos/private/cine-agent-prompts
git worktree remove /Users/ravivtrichter/repos/private/cine-agent-cli
```
