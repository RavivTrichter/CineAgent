"""Assistant API — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from assistant.config import AssistantSettings
from assistant.conversation.sqlite_store import SQLiteConversationStore
from assistant.exceptions import CineAssistError
from assistant.llm.base import LLMProvider
from assistant.llm.claude_provider import ClaudeProvider
from assistant.providers.cinema import CinemaProvider
from assistant.providers.omdb import OMDBProvider
from assistant.providers.tmdb import TMDBProvider
from assistant.services.assistant_service import AssistantService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _create_llm_provider(settings: AssistantSettings) -> LLMProvider:
    """Factory to create the configured LLM provider."""
    if settings.llm_provider == "gemini":
        from assistant.llm.gemini_provider import GeminiProvider
        return GeminiProvider(settings)
    return ClaudeProvider(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = AssistantSettings()
    logger.info("Starting Assistant API...")

    store = SQLiteConversationStore(settings.database_path)
    await store.init_db()

    llm = _create_llm_provider(settings)
    logger.info("Using LLM provider: %s", settings.llm_provider)
    tmdb = TMDBProvider(settings.tmdb_api_key, settings.tmdb_base_url)
    omdb = OMDBProvider(settings.omdb_api_key, settings.omdb_base_url)
    cinema = CinemaProvider(settings.cinema_api_base_url)

    service = AssistantService(
        llm=llm,
        store=store,
        providers={"tmdb": tmdb, "omdb": omdb, "cinema": cinema},
        settings=settings,
    )

    app.state.service = service
    app.state.store = store

    logger.info("Assistant API ready.")
    yield

    await tmdb.close()
    await omdb.close()
    await cinema.close()
    logger.info("Assistant API shut down.")


app = FastAPI(title="CineAssist API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(CineAssistError)
async def cine_assist_error_handler(request: Request, exc: CineAssistError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
    )


# --- Request/Response models ---


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    text: str
    confidence: str
    thinking: str | None = None
    tool_calls_made: list[dict] = []
    hallucination_flags: str | None = None


class ConversationSummary(BaseModel):
    id: str
    title: str | None = None
    updated_at: str
    preview: str | None = None


# --- Endpoints ---


@app.post("/conversations")
async def create_conversation(request: Request):
    store = request.app.state.store
    conversation = await store.create_conversation()
    return {"id": conversation.id}


@app.get("/conversations")
async def list_conversations(request: Request):
    store = request.app.state.store
    conversations = await store.list_conversations()
    result = []
    for conv in conversations:
        # Get last message as preview
        preview = None
        if conv.messages:
            preview = conv.messages[-1].content[:80]
        result.append(
            {
                "id": conv.id,
                "title": conv.title,
                "updated_at": conv.updated_at.isoformat(),
                "preview": preview,
            }
        )
    return result


@app.get("/conversations/{conversation_id}")
async def get_conversation(request: Request, conversation_id: str):
    store = request.app.state.store
    conversation = await store.get_conversation(conversation_id)
    return {
        "id": conversation.id,
        "title": conversation.title,
        "summary": conversation.summary,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role.value,
                "content": msg.content,
                "confidence": msg.confidence.value if msg.confidence else None,
                "thinking": msg.thinking,
                "tool_calls": msg.tool_calls,
                "tool_results": msg.tool_results,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in conversation.messages
        ],
    }


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(request: Request, conversation_id: str):
    store = request.app.state.store
    await store.delete_conversation(conversation_id)
    return {"status": "deleted"}


@app.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(
    request: Request, conversation_id: str, chat_request: ChatRequest
):
    service = request.app.state.service
    result = await service.chat(conversation_id, chat_request.message)
    return ChatResponse(**result)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cine-assist"}
