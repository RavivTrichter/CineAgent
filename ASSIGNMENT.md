# How CineAssist Addresses the Assignment Requirements

This document maps each requirement from the assignment to the specific implementation decisions and code locations in CineAssist.

---

## 1. Conversation-Oriented Design

### Assistant Purpose
**Requirement:** Handle at least three different types of queries or tasks.

CineAssist handles five distinct query types:

| Query Type | Example | Tools Used |
|---|---|---|
| Movie discovery | "Find me a good sci-fi movie" | `search_movies`, `get_similar_movies`, `get_trending_movies` |
| Movie information | "Tell me about Sinners" | `get_movie_details`, `get_movie_ratings` |
| Showtime lookup | "What's playing tonight in Tel Aviv?" | `get_nearby_cinemas`, `get_showtimes` |
| Ticket booking | "Book 2 tickets for Sinners at 8pm" | `book_tickets` (with mandatory confirmation) |
| Subjective recommendations | "What's a good date night movie?" | LLM knowledge, optionally grounded with `search_movies` |

**Code:** `assistant/llm/tools.py` (tool definitions), `assistant/services/assistant_service.py` (system prompt)

### Context & Continuity
**Requirement:** Track conversational context for multi-turn interactions.

Two mechanisms work together:

1. **Sliding window** — The last 20 messages are sent in full to the LLM, preserving recent context for follow-up questions like "What about the evening shows?" or "Book that one."

2. **Context summarization** — When a conversation exceeds 30 messages, older messages are summarized by the LLM into a concise paragraph. This summary is prepended to the context window, so the assistant remembers earlier topics without exceeding token limits.

**Code:** `assistant/services/assistant_service.py` — `_build_context()` and `_maybe_summarize()`

### Interaction Flow
**Requirement:** Natural, user-friendly conversation.

- The system prompt instructs the LLM to ask clarifying questions for ambiguous queries rather than guessing
- Booking requires explicit confirmation with a full summary before proceeding
- Error messages are human-readable ("I couldn't find showtimes for that movie" instead of raw error codes)
- Tool failures are fed back to the LLM as context, allowing it to explain the issue or try alternatives

---

## 2. Advanced Prompt Engineering

### Prompt Crafting
**Requirement:** Thoughtful prompt design for accurate, context-relevant answers.

The system prompt (`assistant/services/assistant_service.py`) is structured into purpose-built sections:

- **Reasoning Process** — Step-by-step instructions for how to approach each query
- **Tool Usage** — Clear rules for when tools are required vs. optional
- **Data Fusion** — How to combine results from multiple APIs
- **Hallucination Prevention** — Specific rules to avoid inventing facts
- **Booking Safety** — Mandatory confirmation flow
- **Scope** — Keeps the assistant focused on movies/cinema

### Multi-Step Reasoning (Chain of Thought)
**Requirement:** At least one method guiding the LLM through chain-of-thought.

Two complementary approaches:

1. **Extended thinking** — Claude's built-in thinking mode is enabled with a 5,000-token budget. The model reasons internally before responding, and the thinking content is preserved for debugging.

2. **Explicit reasoning steps** — The system prompt defines a 5-step process:
   - UNDERSTAND: What is the user asking?
   - PLAN: Which tools do I need?
   - EXECUTE: Call the tools
   - VERIFY: Do results make sense? Do sources agree?
   - RESPOND: Synthesize a grounded answer

**Code:** `assistant/llm/claude_provider.py` (thinking config), system prompt in `assistant/services/assistant_service.py`

### Control Strategies
**Requirement:** Techniques to reduce hallucinations and off-topic responses.

- **Mandatory tool use for facts** — The prompt explicitly lists which categories of information require tool verification (ratings, prices, cast, showtimes)
- **Scope boundaries** — Off-topic questions are redirected back to the movie domain
- **Source attribution** — The prompt instructs the LLM to ground answers in tool data and indicate when using general knowledge
- **Verification step** — "If your answer includes a specific number that didn't come from a tool, STOP and verify"

---

## 3. Technical Implementation

### Interface
**Requirement:** CLI required; web UI optional.

Both are provided:

- **CLI** — Command-line interface for terminal-based interaction (see `README.md` for usage)
- **Web UI** — Streamlit chat interface with conversation sidebar, confidence badges, and debug panel

**Code:** `assistant/streamlit_app.py` (web UI)

### LLM Model
**Requirement:** Integrate with any LLM API.

Uses **Claude Opus 4.6** (Anthropic) with extended thinking and tool use. The `LLMProvider` ABC allows adding other providers (e.g., GPT, Gemini) with zero changes to the assistant service.

**Code:** `assistant/llm/base.py` (ABC), `assistant/llm/claude_provider.py`

---

## 4. External Data Integration

### API Connections
**Requirement:** At least two external APIs.

Three external APIs are integrated:

| API | Purpose | Provider Class |
|---|---|---|
| **TMDB** (The Movie Database) | Movie search, details, cast, similar movies, trending | `assistant/providers/tmdb.py` |
| **OMDB** (Open Movie Database) | Ratings (IMDb, Rotten Tomatoes, Metacritic), box office, awards | `assistant/providers/omdb.py` |
| **Cinema API** (internal) | Cinemas, showtimes, ticket booking | `assistant/providers/cinema.py` |

### Data Fusion
**Requirement:** Combine external data with LLM knowledge accurately.

The system prompt has explicit data fusion instructions:

- TMDB provides movie details (cast, crew, genres, overview) while OMDB provides aggregated ratings and box office — the LLM is instructed to present a **unified view** combining both
- When sources disagree (e.g., different runtimes), the LLM is told to mention both values and note the discrepancy
- Tool data always takes precedence over LLM training knowledge for factual claims

The agentic loop supports this naturally: the LLM can call multiple tools in sequence (e.g., `search_movies` → `get_movie_details` → `get_movie_ratings`) and synthesize all results into one response.

**Code:** `assistant/services/assistant_service.py` — `_agentic_loop()`, system prompt data fusion section

### Decision Logic
**Requirement:** Clear strategy for when to use external data vs. LLM knowledge.

The system prompt defines two clear categories:

**ALWAYS use tools for:** specific movie facts, ratings, cast, showtimes, prices, availability, trending movies

**MAY use general knowledge for:** themes, mood-based recommendations, genre comparisons, film history

The confidence scoring system reflects this decision:

| Confidence | Meaning | Triggered When |
|---|---|---|
| `VERIFIED` | All data comes from tools | All tool calls succeeded |
| `MIXED` | Partial tool data | Some tools succeeded, some failed |
| `GENERAL_KNOWLEDGE` | LLM knowledge only | No tools were called |

**Code:** `assistant/services/assistant_service.py` — `_compute_confidence()`

---

## 5. Hallucination Detection & Management

**Requirement:** Methods to detect potential hallucinations and misinformation.

### Prevention (Prompt-Level)
The system prompt contains 6 specific hallucination prevention rules, including:
- Never invent movie facts — use tools or say "I don't have verified data"
- If a tool returns no results, be honest — don't fabricate alternatives
- If your answer includes an unverified number, stop and use the appropriate tool

### Detection (Code-Level)
A post-processing heuristic (`_detect_hallucination_risk()`) scans the LLM's response for factual-looking claims that aren't backed by tool data:

| Pattern Detected | Without Tool Data | Risk Flag |
|---|---|---|
| "7.8/10" or "92%" | No `get_movie_ratings` called | Rating reference without verification |
| "₪45" or "35 ILS" | No `get_showtimes` called | Price claim without showtime data |
| "$200 million" | No OMDB data | Box office figure without verification |

Detected risks are:
- Logged as warnings for monitoring
- Returned in the API response (`hallucination_flags` field) for client-side display

### Confidence Scoring (User-Facing)
The confidence badge (VERIFIED / MIXED / GENERAL_KNOWLEDGE) gives the user a clear signal of how much of the response is grounded in external data vs. LLM knowledge.

**Code:** `assistant/services/assistant_service.py` — `_detect_hallucination_risk()`, `_compute_confidence()`

---

## Architecture Decisions

For a full technical deep-dive into the class hierarchy, agentic loop, and production considerations, see [ARCHITECTURE.md](ARCHITECTURE.md).
