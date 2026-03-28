"""Assistant service — orchestrates LLM, tools, and conversation."""

import json
import re
from datetime import date

import structlog

from assistant.config import AssistantSettings
from assistant.conversation.base import ConversationStore
from assistant.conversation.models import (
    ConfidenceLevel,
    Message,
    MessageRole,
)
from assistant.exceptions import ProviderError, ToolExecutionError
from assistant.llm.base import LLMProvider, LLMResponse
from assistant.llm.tools import TOOL_REGISTRY, TOOLS

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """\
You are CineAssist, a knowledgeable and friendly movie assistant for Israeli cinema-goers.

## REASONING PROCESS
For every user message, follow this chain of thought:
1. UNDERSTAND: What is the user asking? Is it factual (needs tools) or subjective (opinions, themes)?
2. PLAN: Which tools do I need? Can I cross-reference multiple sources for accuracy?
3. EXECUTE: Call the tools and gather data.
4. VERIFY: Do the results make sense? Do multiple sources agree? Flag any discrepancies.
5. RESPOND: Synthesize a clear, grounded answer. Cite where data came from.

## TOOL USAGE — WHEN TO USE EXTERNAL DATA vs. LLM KNOWLEDGE

ALWAYS use tools for:
- Any specific movie fact: cast, director, ratings, box office, runtime, release date
- Current trending movies or new releases
- Ratings comparisons across sources (IMDb, Rotten Tomatoes, Metacritic)

Use CINEMA tools (get_showtimes, get_nearby_cinemas, book_tickets) ONLY when the user \
explicitly mentions going out to the movies, asks what's playing at cinemas, wants to book \
tickets, or asks about local screenings. Do NOT check cinema showtimes for general movie \
recommendations or discovery queries.

You MAY use general knowledge for:
- Movie themes, tone, and mood descriptions
- Genre-based recommendations ("something like a feel-good comedy")
- Film history, movements, and general cinema knowledge
- Comparisons of genres or filmmaking styles

When recommending movies by genre or mood, do ONE search on TMDB (e.g., search_movies or \
get_trending_movies), then respond with the results. Do NOT burn multiple tool calls searching \
for individual titles one by one — synthesize your answer from the search results you already have.

## DATA FUSION — COMBINING MULTIPLE SOURCES
When you have data from multiple tools (e.g., TMDB details + OMDB ratings):
- Present a unified view: combine cast from TMDB with ratings from OMDB in one response.
- If sources disagree (e.g., different runtimes), mention both values and note the discrepancy.
- Always prefer real-time tool data over your training knowledge for factual claims.

## HALLUCINATION PREVENTION — CRITICAL RULES
1. NEVER invent movie facts. If you don't have tool data for a specific claim, say so explicitly. \
Use phrases like "Based on the data I found..." or "I don't have verified data for that."
2. If a tool returns no results or an error, tell the user honestly. Do NOT fabricate alternatives \
or make up similar-sounding movie titles.
3. Do NOT guess showtimes, prices, or seat availability. These change constantly and MUST come \
from the cinema system.
4. When a user asks about a movie you're unsure of, SEARCH FIRST. Do not assume you know \
the correct title, cast, or plot from memory alone.
5. If you notice your answer includes a specific number (rating, year, box office figure) that \
didn't come from a tool, STOP and use the appropriate tool to verify it.
6. For award nominations/wins, cross-reference with tool data when available rather than relying \
on training data which may be outdated.

## BOOKING SAFETY
Before booking tickets, ALWAYS:
1. Present the FULL booking summary: movie title, cinema name, date, time, number of tickets, \
price per ticket, and total cost.
2. Ask for explicit confirmation ("Shall I go ahead and book?").
3. Never book without user approval — this involves real money.

## RESPONSE FORMATTING
- List each movie on its own line, using markdown bullet points or numbered lists. \
NEVER cram multiple movies onto a single line.
- Format: **Title** (Year) — brief description, rating if available.
- Include ratings when available (e.g., "IMDb: 7.8/10, RT: 92%").
- Prices are in Israeli Shekels. Write prices as "42 ILS" or "35-55 ILS" (do NOT use ₪ symbol).
- Available cinemas are in the Tel Aviv metropolitan area.
- Be conversational, helpful, and concise.
- If a query is ambiguous, ask clarifying questions rather than guessing.

## SCOPE
Stay focused on movies, cinema, and entertainment. For unrelated questions, politely redirect: \
"I'm CineAssist, your movie assistant! I can help with movie info, ratings, showtimes, and bookings."
"""


class AssistantService:
    def __init__(
        self,
        llm: LLMProvider,
        store: ConversationStore,
        providers: dict,
        settings: AssistantSettings,
    ):
        self.llm = llm
        self.store = store
        self.providers = providers
        self.settings = settings

    async def chat(self, conversation_id: str, user_message: str) -> dict:
        """Process a user message and return the assistant's response."""
        conversation = await self.store.get_conversation(conversation_id)

        # Save user message
        user_msg = Message(role=MessageRole.USER, content=user_message)
        await self.store.add_message(conversation_id, user_msg)

        # Auto-title from first message
        if len(conversation.messages) == 0:
            title = user_message[:60] + ("..." if len(user_message) > 60 else "")
            await self.store.update_title(conversation_id, title)

        # Build context
        conversation = await self.store.get_conversation(conversation_id)
        context_messages = self._build_context(conversation)

        # Run the agentic loop
        result = await self._agentic_loop(context_messages)

        # Compute confidence and check for hallucination risk
        confidence = self._compute_confidence(result)
        hallucination_risk = self._detect_hallucination_risk(
            result.get("text") or "", result["tool_results"]
        )
        if hallucination_risk:
            logger.warning(
                "Hallucination risk in conversation %s: %s",
                conversation_id, hallucination_risk,
            )

        # Save assistant response
        assistant_msg = Message(
            role=MessageRole.ASSISTANT,
            content=result["text"] or "",
            confidence=confidence,
            thinking=result["thinking"],
            tool_calls=[tc["name"] for tc in result["tool_calls_made"]],
            tool_results=result["tool_results"],
        )
        await self.store.add_message(conversation_id, assistant_msg)

        # Check if summarization needed
        await self._maybe_summarize(conversation_id)

        return {
            "text": result["text"] or "",
            "confidence": confidence.value,
            "thinking": result["thinking"],
            "tool_calls_made": result["tool_calls_made"],
            "hallucination_flags": hallucination_risk,
        }

    async def _agentic_loop(self, context_messages: list[dict]) -> dict:
        """Run the tool-use loop until we get a final text response."""
        messages = list(context_messages)
        all_tool_calls: list[dict] = []
        all_tool_results: list[dict] = []
        all_thinking: list[str] = []

        for iteration in range(self.settings.max_tool_iterations):
            logger.info("Agentic loop iteration %d", iteration + 1)

            response: LLMResponse = await self.llm.chat(
                messages=messages,
                system_prompt=f"Today's date is {date.today().isoformat()}.\n\n{SYSTEM_PROMPT}",
                tools=TOOLS,
            )

            if response.thinking:
                all_thinking.append(response.thinking)
                logger.debug("Thinking: %s", response.thinking[:200])

            if response.stop_reason != "tool_use":
                return {
                    "text": response.text,
                    "thinking": "\n\n".join(all_thinking) if all_thinking else None,
                    "tool_calls_made": all_tool_calls,
                    "tool_results": all_tool_results,
                }

            # Use raw content blocks to preserve thinking signatures
            messages.append({"role": "assistant", "content": response.raw_content_blocks})

            # Execute tools and build results
            tool_results_content = []
            for tc in response.tool_calls:
                logger.info("Executing tool: %s(%s)", tc["name"], tc["input"])
                result = await self._execute_tool(tc["name"], tc["input"])
                all_tool_calls.append(tc)
                all_tool_results.append({"tool": tc["name"], "result": result})

                tool_results_content.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": json.dumps(result),
                    }
                )

            messages.append({"role": "user", "content": tool_results_content})

        # Exhausted iterations
        logger.warning("Agentic loop exhausted after %d iterations", self.settings.max_tool_iterations)
        return {
            "text": response.text or "I've gathered some information but couldn't complete the request. Please try again.",
            "thinking": "\n\n".join(all_thinking) if all_thinking else None,
            "tool_calls_made": all_tool_calls,
            "tool_results": all_tool_results,
        }

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """Execute a tool call and return the result."""
        if tool_name not in TOOL_REGISTRY:
            raise ToolExecutionError(tool_name, "Unknown tool")

        provider_key, method_name = TOOL_REGISTRY[tool_name]
        provider = self.providers.get(provider_key)
        if not provider:
            raise ToolExecutionError(tool_name, f"Provider '{provider_key}' not available")

        try:
            method = getattr(provider, method_name)
            result = await method(**tool_input)
            return {"status": "success", "data": result}
        except ProviderError as e:
            logger.warning("Tool %s failed: %s", tool_name, e.message)
            return {"status": "error", "error": e.message}
        except Exception as e:
            logger.error("Unexpected error in tool %s: %s", tool_name, e)
            return {"status": "error", "error": str(e)}

    def _compute_confidence(self, result: dict) -> ConfidenceLevel:
        """Determine confidence level based on tool usage and hallucination risk."""
        tool_calls = result["tool_calls_made"]
        tool_results = result["tool_results"]
        text = result.get("text") or ""

        if not tool_calls:
            # Check for hallucination risk: factual claims without tool backing
            risk = self._detect_hallucination_risk(text, tool_results)
            if risk:
                logger.warning("Hallucination risk detected (no tools used): %s", risk)
            return ConfidenceLevel.GENERAL_KNOWLEDGE

        successful = [
            tr for tr in tool_results if tr["result"].get("status") == "success"
        ]

        if len(successful) == len(tool_calls):
            return ConfidenceLevel.VERIFIED
        elif len(successful) > 0:
            return ConfidenceLevel.MIXED
        else:
            return ConfidenceLevel.GENERAL_KNOWLEDGE

    def _detect_hallucination_risk(self, text: str, tool_results: list[dict]) -> str | None:
        """Heuristic check for potential hallucinations in the response.

        Looks for factual-sounding claims (ratings, prices, years, specific numbers)
        that aren't backed by tool data. Returns a description of the risk, or None.
        """
        risks = []

        # Check for rating patterns without tool data
        has_rating_data = any(
            tr["tool"] in ("get_movie_ratings", "get_movie_details", "search_movies")
            and tr["result"].get("status") == "success"
            for tr in tool_results
        )
        rating_patterns = [
            r"\b\d+(\.\d+)?/10\b",           # "7.8/10"
            r"\b\d{1,3}%\b",                  # "92%"
            r"Rotten Tomatoes",
            r"Metacritic",
            r"IMDb",
        ]
        if not has_rating_data:
            for pattern in rating_patterns:
                if re.search(pattern, text):
                    risks.append(f"Rating reference '{pattern}' without tool verification")
                    break

        # Check for price claims without showtime data
        has_showtime_data = any(
            tr["tool"] in ("get_showtimes", "book_tickets")
            and tr["result"].get("status") == "success"
            for tr in tool_results
        )
        if not has_showtime_data and re.search(r"₪\s*\d+|\d+\s*ILS|\d+\s*shekels", text, re.IGNORECASE):
            risks.append("Price claim without showtime/booking data")

        # Check for specific box office figures without OMDB data
        if not has_rating_data and re.search(r"\$[\d,]+\s*(million|billion|M|B)", text, re.IGNORECASE):
            risks.append("Box office figure without OMDB verification")

        return "; ".join(risks) if risks else None

    def _build_context(self, conversation) -> list[dict]:
        """Build message context from conversation history."""
        messages = conversation.messages
        result: list[dict] = []

        # Prepend summary if available
        if conversation.summary:
            result.append(
                {
                    "role": "user",
                    "content": f"[Previous conversation summary: {conversation.summary}]",
                }
            )
            result.append(
                {
                    "role": "assistant",
                    "content": "I have the context from our earlier conversation. How can I help you?",
                }
            )

        # Add recent messages
        recent = messages[-self.settings.context_window_size :]
        for msg in recent:
            if msg.role in (MessageRole.USER, MessageRole.ASSISTANT):
                result.append({"role": msg.role.value, "content": msg.content})

        return result

    async def _maybe_summarize(self, conversation_id: str) -> None:
        """Summarize older messages if conversation exceeds threshold."""
        messages = await self.store.get_messages(conversation_id)
        if len(messages) <= self.settings.summary_threshold:
            return

        conversation = await self.store.get_conversation(conversation_id)
        cutoff = len(messages) - self.settings.context_window_size
        old_messages = messages[:cutoff]
        existing_summary = conversation.summary or ""

        # Build summarization prompt
        formatted = "\n".join(
            f"[{m.role.value}]: {m.content}"
            for m in old_messages
            if m.role in (MessageRole.USER, MessageRole.ASSISTANT)
        )

        prompt = (
            "Summarize the following conversation history into a concise paragraph. "
            "Preserve: key topics discussed, movies mentioned, user preferences, "
            "any bookings made, and important context.\n\n"
        )
        if existing_summary:
            prompt += f"Previous summary: {existing_summary}\n\n"
        prompt += f"Messages to summarize:\n{formatted}\n\nWrite a concise summary (3-5 sentences):"

        logger.info("Summarizing conversation %s (%d old messages)", conversation_id, len(old_messages))

        response = await self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a conversation summarizer. Be concise and factual.",
        )

        if response.text:
            await self.store.update_summary(conversation_id, response.text)
