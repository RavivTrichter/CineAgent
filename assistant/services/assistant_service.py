"""Assistant service — orchestrates LLM, tools, and conversation."""

import json
import logging

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

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are CineAssist, a knowledgeable and friendly movie assistant for Israeli cinema-goers.

CRITICAL RULES:
1. For any factual claim about a specific movie (cast, ratings, box office, release date, \
showtimes, prices, availability), you MUST use the appropriate tool. Never invent or guess \
this information.
2. If a tool returns no results or an error, tell the user honestly. Do not fabricate alternatives.
3. Before booking tickets, ALWAYS present the full booking details (movie, cinema, time, seats, \
price per ticket, total cost) and ask for explicit confirmation. Never book without user approval.
4. For subjective questions (movie themes, mood-based recommendations, comparisons), you may use \
your general knowledge but ground it in tool data when possible.
5. Think step by step: first determine what the user needs, then decide which tools (if any) \
are required, then synthesize a clear response.
6. Format movie results clearly with title, year, and a brief description. Use ratings data \
from tools when available.
7. Prices are in Israeli Shekels (ILS / ₪).
8. Available cinemas are in the Tel Aviv metropolitan area.

CAPABILITIES:
- Search and discover movies (TMDB)
- Get detailed ratings from IMDb, Rotten Tomatoes, Metacritic (OMDB)
- Find showtimes at local cinemas
- Book movie tickets (requires user confirmation)

Always be conversational, helpful, and concise. If a query is ambiguous, ask clarifying questions.
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

        # Compute confidence
        confidence = self._compute_confidence(result)

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
                system_prompt=SYSTEM_PROMPT,
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
        """Determine confidence level based on tool usage."""
        tool_calls = result["tool_calls_made"]
        tool_results = result["tool_results"]

        if not tool_calls:
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
